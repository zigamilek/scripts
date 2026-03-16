#!/usr/bin/env python3
import argparse
import configparser
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from dotenv import load_dotenv


RSS_BASE_URL = "https://broadcasthe.net/feeds.php"
COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.13; ko; rv:1.9.1b2) Gecko/20081201 Firefox/60.0",
    "Accept": "image/gif, image/x-xbitmap, image/jpeg, image/pjpeg, image/png, */*",
    "Accept-Charset": "iso-8859-1,*,utf-8",
    "Accept-Language": "en-US",
}
ENV_VARS = (
    "BROADCASTHENET_UID",
    "BROADCASTHENET_PASSKEY",
    "BROADCASTHENET_AUTH",
    "BROADCASTHENET_AUTHKEY",
)


def load_repo_dotenv() -> None:
    current_dir = Path(__file__).resolve().parent
    while True:
        env_file = current_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            return
        if current_dir.parent == current_dir:
            return
        current_dir = current_dir.parent


def resolve_config_path(cli_value: Optional[str]) -> Path:
    script_dir = Path(__file__).resolve().parent

    if cli_value:
        path = Path(cli_value).expanduser()
        print(f"warning: using {path} from command line")
        return path

    local_path = script_dir / "broadcasthenet.local.ini"
    if local_path.exists():
        print(f"warning: using {local_path} as default config file")
        return local_path

    default_path = script_dir / "broadcasthenet.ini"
    print(f"warning: using {default_path} as default config file")
    return default_path


def get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing {name} environment variable.")
    return value


def load_config(path: Path) -> configparser.ConfigParser:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config.read(path)

    if "setup" not in config:
        raise RuntimeError("no [setup] section in configfile")

    for key in ("cookies", "inidb"):
        if key not in config["setup"] or not config["setup"][key].strip():
            raise RuntimeError(f"no {key}= in section [setup] in configfile")

    return config


def load_fetched_db(path: Path, debug: bool) -> configparser.ConfigParser:
    path.parent.mkdir(parents=True, exist_ok=True)

    db = configparser.ConfigParser(interpolation=None)
    db.optionxform = str

    if path.exists():
        db.read(path)
        debug_print(debug, f"DEBUG: {path} exists and is readable")
    else:
        debug_print(debug, f"DEBUG: initializing inidb {path}")
        db["fetched"] = {}
        with path.open("w", encoding="utf-8") as handle:
            db.write(handle)

    if "fetched" not in db:
        db["fetched"] = {}

    return db


def save_fetched_db(db: configparser.ConfigParser, path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        db.write(handle)


def build_opener(cookie_file: Path) -> urllib.request.OpenerDirector:
    if not cookie_file.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")

    cookie_jar = MozillaCookieJar(str(cookie_file))
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def fetch_url(
    opener: urllib.request.OpenerDirector,
    url: str,
) -> tuple[bytes, urllib.response.addinfourl]:
    request = urllib.request.Request(url, headers=COMMON_HEADERS)
    response = opener.open(request)
    try:
        return response.read(), response
    except Exception:
        response.close()
        raise


def fetch_text(opener: urllib.request.OpenerDirector, url: str) -> str:
    data, response = fetch_url(opener, url)
    try:
        charset = response.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="replace")
    finally:
        response.close()


def parse_items(xml_text: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(xml_text)
    items: list[dict[str, str]] = []
    for item in root.findall("./channel/item"):
        items.append(
            {
                "link": item.findtext("link", default=""),
                "title": item.findtext("title", default=""),
                "description": item.findtext("description", default=""),
            }
        )
    return items


def parse_size_mb(description: str) -> float:
    match = re.search(r"([0-9.]+)\s*(GB|MB)", description, re.IGNORECASE)
    if not match:
        return 0.0

    size = float(match.group(1))
    unit = match.group(2).upper()
    if unit == "GB":
        size *= 1024
    return size


def extract_filename(response: urllib.response.addinfourl, fallback_url: str) -> str:
    content_disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r'filename="([^"]+)"', content_disposition, re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(r"filename=([^;]+)", content_disposition, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"')

    parsed = urllib.parse.urlparse(fallback_url)
    filename = Path(parsed.path).name
    if filename:
        return filename

    raise RuntimeError(f"Unable to determine torrent filename for {fallback_url}")


def get_torrent_filename(opener: urllib.request.OpenerDirector, url: str) -> str:
    _, response = fetch_url(opener, url)
    try:
        return extract_filename(response, url)
    finally:
        response.close()


def download_torrent(opener: urllib.request.OpenerDirector, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=COMMON_HEADERS)
    with opener.open(request) as response, destination.open("wb") as handle:
        handle.write(response.read())


def iter_filter_sections(config: configparser.ConfigParser) -> list[str]:
    return [section for section in config.sections() if section.lower().startswith("filter")]


def compile_regex(pattern: str, section: str, key: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise RuntimeError(f"Invalid regex for [{section}] {key}: {exc}") from exc


def debug_print(enabled: bool, message: str) -> None:
    if enabled:
        print(message)


def build_rss_url() -> str:
    params = {
        "feed": "torrents_all",
        "user": get_env("BROADCASTHENET_UID"),
        "auth": get_env("BROADCASTHENET_AUTH"),
        "passkey": get_env("BROADCASTHENET_PASSKEY"),
        "authkey": get_env("BROADCASTHENET_AUTHKEY"),
    }
    return f"{RSS_BASE_URL}?{urllib.parse.urlencode(params)}"


def process_feed(config: configparser.ConfigParser, config_path: Path) -> None:
    setup = config["setup"]
    debug = setup.getboolean("debug", fallback=False)
    cookie_file = Path(setup["cookies"]).expanduser()
    fetched_db_path = Path(setup["inidb"]).expanduser()
    fetched_db = load_fetched_db(fetched_db_path, debug)
    opener = build_opener(cookie_file)

    debug_print(debug, f"DEBUG:============={int(time.time())}=============")
    rss_url = build_rss_url()
    xml_text = fetch_text(opener, rss_url)
    items = parse_items(xml_text)

    for item in items:
        title = item["title"]
        link = item["link"]
        size_mb = parse_size_mb(item["description"])

        debug_print(debug, f"DEBUG:        title | {title}")

        for section in iter_filter_sections(config):
            section_config = config[section]
            hot_pattern = section_config.get("hot", "").strip()
            if not hot_pattern:
                continue

            if not compile_regex(hot_pattern, section, "hot").search(title):
                continue

            debug_print(debug, f"DEBUG:                 {section} | {title} | HOT: {hot_pattern}")

            not_pattern = section_config.get("not", "").strip()
            if not_pattern and compile_regex(not_pattern, section, "not").search(title):
                debug_print(debug, f"DEBUG:                 {section} | {title} | NOT: {not_pattern}")
                continue

            filename = get_torrent_filename(opener, link)
            if fetched_db["fetched"].get(filename):
                debug_print(debug, f"DEBUG:                 already fetched {filename}")
                continue

            min_size = float(section_config.get("min", "-1"))
            max_size = float(section_config.get("max", "10000000"))
            if not (size_mb > min_size and size_mb < max_size):
                debug_print(debug, f"DEBUG:                 size not {min_size} < {size_mb} < {max_size}")
                continue

            target_dir_value = section_config.get("path", "").strip()
            if not target_dir_value:
                raise RuntimeError(f"Missing path= in section [{section}] in configfile {config_path}")

            target_dir = Path(target_dir_value).expanduser()
            target_file = target_dir / filename

            debug_print(debug, f"DEBUG:                 Fetch {filename}")
            debug_print(debug, f"DEBUG:                Fetching {link}")
            debug_print(debug, f"DEBUG:                File destination {target_file}")

            download_torrent(opener, link, target_file)

            fetched_db["fetched"][filename] = str(int(time.time()))
            save_fetched_db(fetched_db, fetched_db_path)

        debug_print(debug, "DEBUG: -------------------------")


def main() -> int:
    load_repo_dotenv()

    parser = argparse.ArgumentParser(description="Download matching Broadcasthe.net torrents.")
    parser.add_argument(
        "config",
        nargs="?",
        help="Optional path to a config file. Defaults to broadcasthenet.local.ini or broadcasthenet.ini.",
    )
    args = parser.parse_args()

    config_path = resolve_config_path(args.config)
    config = load_config(config_path)
    process_feed(config, config_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
