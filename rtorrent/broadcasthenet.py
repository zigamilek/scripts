#!/usr/bin/env python3
import argparse
import configparser
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from dotenv import load_dotenv


RSS_BASE_URL = "https://broadcasthe.net/feeds.php"
REQUEST_TIMEOUT_SECONDS = 30
SCRIPT_DIR = Path(__file__).resolve().parent
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


@dataclass(frozen=True)
class Credentials:
    uid: str
    passkey: str
    auth: str
    authkey: str


@dataclass(frozen=True)
class SetupConfig:
    cookies: Path
    inidb: Path
    debug: bool


@dataclass(frozen=True)
class FilterRule:
    name: str
    path: Path
    hot_pattern: str
    hot_regex: re.Pattern[str]
    not_pattern: str
    not_regex: Optional[re.Pattern[str]]
    min_size: float
    max_size: float

    def matches_title(self, title: str) -> bool:
        return bool(self.hot_regex.search(title))

    def excludes_title(self, title: str) -> bool:
        return bool(self.not_regex and self.not_regex.search(title))

    def matches_size(self, size_mb: float) -> bool:
        return self.min_size < size_mb < self.max_size


@dataclass(frozen=True)
class FeedItem:
    link: str
    title: str
    description: str


@dataclass
class FetchedDB:
    path: Path
    config: configparser.ConfigParser

    @classmethod
    def load(cls, path: Path, debug: bool) -> "FetchedDB":
        path.parent.mkdir(parents=True, exist_ok=True)

        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str

        if path.exists():
            config.read(path)
            debug_print(debug, f"DEBUG: {path} exists and is readable")
        else:
            debug_print(debug, f"DEBUG: initializing inidb {path}")
            config["fetched"] = {}
            instance = cls(path=path, config=config)
            instance.save()
            return instance

        if "fetched" not in config:
            config["fetched"] = {}

        return cls(path=path, config=config)

    def contains(self, filename: str) -> bool:
        return self.config["fetched"].get(filename) is not None

    def add(self, filename: str) -> None:
        self.config["fetched"][filename] = str(int(time.time()))
        self.save()

    def save(self) -> None:
        temp_path = self.path.with_name(f".{self.path.name}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            self.config.write(handle)
        os.replace(temp_path, self.path)


def load_repo_dotenv() -> None:
    current_dir = SCRIPT_DIR
    while True:
        env_file = current_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            return
        if current_dir.parent == current_dir:
            return
        current_dir = current_dir.parent


def resolve_config_path(cli_value: Optional[str]) -> Path:
    if cli_value:
        path = Path(cli_value).expanduser()
        print(f"warning: using {path} from command line")
        return path

    local_path = SCRIPT_DIR / "broadcasthenet.local.ini"
    if local_path.exists():
        print(f"warning: using {local_path} as default config file")
        return local_path

    default_path = SCRIPT_DIR / "broadcasthenet.ini"
    print(f"warning: using {default_path} as default config file")
    return default_path


def compile_regex(pattern: str, section: str, key: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        raise RuntimeError(f"Invalid regex for [{section}] {key}: {exc}") from exc


def debug_print(enabled: bool, message: str) -> None:
    if enabled:
        print(message)


def build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers=COMMON_HEADERS)


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


def load_setup_config(config: configparser.ConfigParser) -> SetupConfig:
    setup = config["setup"]
    return SetupConfig(
        cookies=Path(setup["cookies"]).expanduser(),
        inidb=Path(setup["inidb"]).expanduser(),
        debug=setup.getboolean("debug", fallback=False),
    )


def load_credentials() -> Credentials:
    values: dict[str, str] = {}
    for name in ENV_VARS:
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Missing {name} environment variable.")
        values[name] = value

    return Credentials(
        uid=values["BROADCASTHENET_UID"],
        passkey=values["BROADCASTHENET_PASSKEY"],
        auth=values["BROADCASTHENET_AUTH"],
        authkey=values["BROADCASTHENET_AUTHKEY"],
    )


def load_filter_rules(
    config: configparser.ConfigParser,
    config_path: Path,
) -> list[FilterRule]:
    rules: list[FilterRule] = []

    for section in config.sections():
        if not section.lower().startswith("filter"):
            continue

        section_config = config[section]
        hot_pattern = section_config.get("hot", "").strip()
        if not hot_pattern:
            continue

        target_dir_value = section_config.get("path", "").strip()
        if not target_dir_value:
            raise RuntimeError(f"Missing path= in section [{section}] in configfile {config_path}")

        not_pattern = section_config.get("not", "").strip()
        rules.append(
            FilterRule(
                name=section,
                path=Path(target_dir_value).expanduser(),
                hot_pattern=hot_pattern,
                hot_regex=compile_regex(hot_pattern, section, "hot"),
                not_pattern=not_pattern,
                not_regex=compile_regex(not_pattern, section, "not") if not_pattern else None,
                min_size=float(section_config.get("min", "-1")),
                max_size=float(section_config.get("max", "10000000")),
            )
        )

    return rules


def build_opener(cookie_file: Path) -> urllib.request.OpenerDirector:
    if not cookie_file.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_file}")

    cookie_jar = MozillaCookieJar(str(cookie_file))
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def fetch_text(opener: urllib.request.OpenerDirector, url: str) -> str:
    with opener.open(build_request(url), timeout=REQUEST_TIMEOUT_SECONDS) as response:
        data = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return data.decode(charset, errors="replace")


def parse_items(xml_text: str) -> list[FeedItem]:
    root = ElementTree.fromstring(xml_text)
    items: list[FeedItem] = []
    for item in root.findall("./channel/item"):
        items.append(
            FeedItem(
                link=item.findtext("link", default=""),
                title=item.findtext("title", default=""),
                description=item.findtext("description", default=""),
            )
        )
    return items


def parse_size_mb(description: str) -> float:
    match = re.search(r"([0-9.]+)\s*(GB|MB)", description, re.IGNORECASE)
    if not match:
        return 0.0

    size = float(match.group(1))
    if match.group(2).upper() == "GB":
        size *= 1024
    return size


def extract_filename(headers, fallback_url: str) -> str:
    content_disposition = headers.get("Content-Disposition", "")
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
    with opener.open(build_request(url), timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return extract_filename(response.headers, url)


def download_torrent(opener: urllib.request.OpenerDirector, url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with opener.open(build_request(url), timeout=REQUEST_TIMEOUT_SECONDS) as response, destination.open("wb") as handle:
        handle.write(response.read())


def build_rss_url(credentials: Credentials) -> str:
    params = {
        "feed": "torrents_all",
        "user": credentials.uid,
        "auth": credentials.auth,
        "passkey": credentials.passkey,
        "authkey": credentials.authkey,
    }
    return f"{RSS_BASE_URL}?{urllib.parse.urlencode(params)}"


def process_feed(config: configparser.ConfigParser, config_path: Path) -> None:
    setup = load_setup_config(config)
    credentials = load_credentials()
    rules = load_filter_rules(config, config_path)
    fetched_db = FetchedDB.load(setup.inidb, setup.debug)
    opener = build_opener(setup.cookies)

    debug_print(setup.debug, f"DEBUG:============={int(time.time())}=============")
    rss_url = build_rss_url(credentials)
    items = parse_items(fetch_text(opener, rss_url))

    for item in items:
        title = item.title
        size_mb = parse_size_mb(item.description)
        resolved_filename: Optional[str] = None

        debug_print(setup.debug, f"DEBUG:        title | {title}")

        for rule in rules:
            if not rule.matches_title(title):
                continue

            debug_print(setup.debug, f"DEBUG:                 {rule.name} | {title} | HOT: {rule.hot_pattern}")

            if rule.excludes_title(title):
                debug_print(setup.debug, f"DEBUG:                 {rule.name} | {title} | NOT: {rule.not_pattern}")
                continue

            if resolved_filename is None:
                resolved_filename = get_torrent_filename(opener, item.link)

            if fetched_db.contains(resolved_filename):
                debug_print(setup.debug, f"DEBUG:                 already fetched {resolved_filename}")
                continue

            if not rule.matches_size(size_mb):
                debug_print(
                    setup.debug,
                    f"DEBUG:                 size not {rule.min_size} < {size_mb} < {rule.max_size}",
                )
                continue

            target_file = rule.path / resolved_filename
            debug_print(setup.debug, f"DEBUG:                 Fetch {resolved_filename}")
            debug_print(setup.debug, f"DEBUG:                Fetching {item.link}")
            debug_print(setup.debug, f"DEBUG:                File destination {target_file}")

            download_torrent(opener, item.link, target_file)
            fetched_db.add(resolved_filename)

        debug_print(setup.debug, "DEBUG: -------------------------")


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
