#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import parse_qs, urlparse

import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


DEFAULT_OUTPUT_DIR = Path(
    "/Users/zigamilek/Library/CloudStorage/Dropbox/Zigec/AI/YouTube video summaries"
)
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SYSTEM_PROMPT_FILE = Path(__file__).with_name("system_prompt.md")
PROCESSED_VIDEO_IDS_FILENAME = "processed_video_ids.txt"

# These are conservative working thresholds for the multi-pass pipeline, chosen
# to leave comfortable headroom for prompts, metadata, and responses. They are
# not direct copies of GPT-5.4's maximum context size, and they are not output
# caps for the model response.
#TRANSCRIPT_CHUNK_TOKEN_LIMIT = 5_000
#NOTE_REDUCTION_TOKEN_LIMIT = 7_000
#FINAL_NOTES_TOKEN_LIMIT = 12_000
TRANSCRIPT_CHUNK_TOKEN_LIMIT = 12_000
NOTE_REDUCTION_TOKEN_LIMIT = 24_000
FINAL_NOTES_TOKEN_LIMIT = 40_000


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoTarget:
    original_input: str
    video_id: str
    canonical_url: str


@dataclass
class TranscriptSegment:
    start_seconds: float
    timestamp: str
    text: str


@dataclass
class VideoMetadata:
    video_id: str
    original_url: str
    title: str
    channel: str | None = None
    channel_url: str | None = None
    upload_date_raw: str | None = None
    publish_date: str | None = None
    duration_seconds: int | None = None
    transcript_language: str | None = None
    transcript_language_code: str | None = None
    transcript_is_generated: bool | None = None

    @property
    def display_title(self) -> str:
        return self.title or f"YouTube video {self.video_id}"

    @property
    def duration_display(self) -> str | None:
        return format_duration(self.duration_seconds)

    @property
    def transcript_display(self) -> str:
        parts: list[str] = []
        if self.transcript_language:
            parts.append(self.transcript_language)
        if self.transcript_language_code:
            parts.append(f"({self.transcript_language_code})")
        base = " ".join(parts).strip() or "Unknown"
        if self.transcript_is_generated is True:
            return f"{base}, auto-generated"
        if self.transcript_is_generated is False:
            return f"{base}, manual"
        return base


@dataclass
class UsageTotals:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: "UsageTotals") -> None:
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens


def load_repo_dotenv() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        env_file = os.path.join(current_dir, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)
            return
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            return
        current_dir = parent_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize YouTube videos from a URL or an input file of URLs."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--url", help="Single YouTube URL or bare video ID.")
    source_group.add_argument(
        "--input-file",
        type=Path,
        help="Text file containing one YouTube URL per line. Blank lines and # comments are ignored.",
    )
    source_group.add_argument(
        "--playlist-url",
        help="YouTube playlist URL. All videos in the playlist are expanded and processed as a batch. Requires yt-dlp.",
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        help="Path to a Netscape-format cookies.txt file for authenticated playlist access (e.g. private playlists).",
    )
    parser.add_argument(
        "--cookies-from-browser",
        help="Browser name to extract cookies from for authenticated playlist access (e.g. 'firefox', 'chrome').",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for Markdown summaries. Defaults to {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use. Defaults to {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--log",
        default=DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help=f"Set the logging level. Defaults to {DEFAULT_LOG_LEVEL}",
    )
    parser.add_argument(
        "--system-prompt-file",
        type=Path,
        help="Optional path to a Markdown file containing the system prompt.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and show what would be processed without fetching transcripts, calling OpenAI, or writing output files.",
    )
    parser.add_argument(
        "--astro",
        action="store_true",
        help="Emit Astro-ready Markdown with YAML frontmatter and flat <videoId>.md filenames.",
    )
    return parser.parse_args()


def get_encoder(model: str):
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def count_tokens(text: str, encoder) -> int:
    return len(encoder.encode(text))


def format_timestamp(total_seconds: float) -> str:
    rounded = max(0, int(total_seconds))
    hours, remainder = divmod(rounded, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_duration(total_seconds: int | None) -> str | None:
    if total_seconds is None:
        return None
    hours, remainder = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


def format_duration_for_filename(total_seconds: int | None) -> str:
    if total_seconds is None:
        return "unknown_duration"

    rounded_minutes = int((int(total_seconds) + 30) // 60)
    hours, minutes = divmod(rounded_minutes, 60)
    if hours:
        return f"{hours}h{minutes}m"
    return f"{minutes}m"


def slugify(value: str, max_length: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text.lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        return "youtube_video"
    return slug[:max_length].rstrip("_") or "youtube_video"


def slugify_hyphen(value: str, max_length: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    if not slug:
        return "unknown"
    return slug[:max_length].rstrip("-") or "unknown"


def build_url_slug(metadata: VideoMetadata) -> str:
    title_part = slugify_hyphen(metadata.title or "youtube-video", max_length=80)
    return f"{title_part}-{metadata.video_id.lower()}"


def build_channel_slug(channel: str | None) -> str:
    return slugify_hyphen(channel or "unknown-channel", max_length=60)


def sanitize_path_component(value: str | None, fallback: str, max_length: int = 180) -> str:
    raw_value = value or ""
    normalized = unicodedata.normalize("NFKD", raw_value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", ascii_text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(".")
    cleaned = cleaned[:max_length].rstrip(" .")
    return cleaned or fallback


def build_log_file_name(args: argparse.Namespace) -> str:
    if args.input_file:
        input_basename = slugify(args.input_file.stem)
        return f"youtube_summarizer_{input_basename}.log"
    if args.url:
        try:
            source_name = extract_video_id(args.url)
        except ValueError:
            source_name = "single"
        return f"youtube_summarizer_{source_name}.log"
    if getattr(args, "playlist_url", None):
        try:
            playlist_id = extract_playlist_id(args.playlist_url)
            return f"youtube_summarizer_playlist_{playlist_id}.log"
        except ValueError:
            return "youtube_summarizer_playlist.log"
    return "youtube_summarizer.log"


def configure_logging(args: argparse.Namespace) -> None:
    log_level = getattr(logging, args.log.upper(), logging.INFO)
    log_file_name = build_log_file_name(args)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file_name, encoding="utf-8"),
        ],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def extract_video_id(value: str) -> str:
    raw = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", raw):
        return raw

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        candidate = path_parts[0]
    elif "youtube.com" in host or "youtube-nocookie.com" in host:
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif path_parts and path_parts[0] in {"embed", "shorts", "live"} and len(path_parts) >= 2:
            candidate = path_parts[1]
        else:
            candidate = None
    else:
        candidate = None

    if candidate and re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate):
        return candidate

    raise ValueError(f"Could not extract a valid YouTube video ID from: {value}")


def extract_playlist_id(value: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if "youtube.com" not in host:
        raise ValueError(f"Not a YouTube playlist URL: {value}")
    list_id = parse_qs(parsed.query).get("list", [None])[0]
    if not list_id:
        raise ValueError(f"Could not extract a playlist ID from: {value}")
    return list_id


def expand_playlist(
    playlist_url: str,
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> tuple[list[str], str | None]:
    """Expand a YouTube playlist into a list of canonical video URLs.

    Returns (video_urls, playlist_title).
    """
    if yt_dlp is None:
        raise RuntimeError(
            "yt-dlp is required for playlist expansion but is not installed. "
            "Install it with: pip install yt-dlp"
        )

    options: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
    }
    if cookies_file:
        options["cookiefile"] = str(resolve_path(cookies_file))
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
    except Exception as exc:
        raise RuntimeError(f"Failed to expand playlist: {exc}") from exc

    if info is None:
        raise RuntimeError(f"yt-dlp returned no data for playlist: {playlist_url}")

    playlist_title = info.get("title")
    entries = info.get("entries") or []

    video_urls: list[str] = []
    for entry in entries:
        if entry is None:
            continue
        video_id = entry.get("id")
        if video_id and re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            video_urls.append(canonical_url(video_id))

    return video_urls, playlist_title


def canonical_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def resolve_path(path: Path) -> Path:
    return path.expanduser().resolve()


def load_system_prompt(override_path: Path | None) -> tuple[str, Path]:
    prompt_path = DEFAULT_SYSTEM_PROMPT_FILE if override_path is None else resolve_path(override_path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt file was not found: {prompt_path}")
    if not prompt_path.is_file():
        raise RuntimeError(f"System prompt path is not a file: {prompt_path}")
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Could not read system prompt file {prompt_path}: {exc}") from exc
    if not prompt_text:
        raise RuntimeError(f"System prompt file is empty: {prompt_path}")
    return prompt_text, prompt_path


def read_input_file(input_file: Path) -> list[str]:
    path = resolve_path(input_file)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"Could not read input file {path}: {exc}") from exc

    urls: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        urls.append(stripped)
    return urls


def build_targets(args: argparse.Namespace) -> tuple[list[VideoTarget], list[str]]:
    failures: list[str] = []

    if getattr(args, "playlist_url", None):
        raw_entries, playlist_title = expand_playlist(
            args.playlist_url,
            cookies_file=getattr(args, "cookies_file", None),
            cookies_from_browser=getattr(args, "cookies_from_browser", None),
        )
        if playlist_title:
            LOGGER.info(f"Playlist: {playlist_title} ({len(raw_entries)} video(s))")
        else:
            LOGGER.info(f"Playlist expanded to {len(raw_entries)} video(s)")
    elif args.url:
        raw_entries = [args.url]
    else:
        raw_entries = read_input_file(args.input_file)

    targets: list[VideoTarget] = []
    seen_video_ids: set[str] = set()

    for entry in raw_entries:
        try:
            video_id = extract_video_id(entry)
        except ValueError as exc:
            if args.url:
                raise RuntimeError(str(exc)) from exc
            failures.append(f"{entry} -> {exc}")
            continue

        if video_id in seen_video_ids:
            LOGGER.info(f"Skipping duplicate entry for video {video_id}: {entry}")
            continue

        seen_video_ids.add(video_id)
        targets.append(
            VideoTarget(
                original_input=entry,
                video_id=video_id,
                canonical_url=canonical_url(video_id),
            )
        )

    if not targets:
        raise RuntimeError("No valid YouTube URLs or video IDs were provided.")

    return targets, failures


def select_transcript(video_id: str):
    api = YouTubeTranscriptApi()
    transcript_list = api.list(video_id)

    def safe_find(method_name: str, languages: Sequence[str]):
        method = getattr(transcript_list, method_name)
        try:
            return method(list(languages))
        except Exception as exc:  # library exceptions vary across versions
            if exc.__class__.__name__ == "NoTranscriptFound":
                return None
            raise

    for method_name in ("find_manually_created_transcript", "find_generated_transcript"):
        transcript = safe_find(method_name, ["en"])
        if transcript is not None:
            return transcript

    available = list(transcript_list)
    if not available:
        raise RuntimeError(f"No transcripts were available for video {video_id}.")

    manual_any = [transcript for transcript in available if not getattr(transcript, "is_generated", False)]
    return manual_any[0] if manual_any else available[0]


def normalize_transcript_entries(raw_entries: Iterable[dict]) -> list[TranscriptSegment]:
    segments: list[TranscriptSegment] = []
    for entry in raw_entries:
        text = clean_whitespace(str(entry.get("text", "")))
        if not text:
            continue
        start_seconds = float(entry.get("start", 0.0))
        segments.append(
            TranscriptSegment(
                start_seconds=start_seconds,
                timestamp=format_timestamp(start_seconds),
                text=text,
            )
        )
    return segments


def fetch_transcript(video_id: str) -> tuple[list[TranscriptSegment], dict]:
    try:
        transcript = select_transcript(video_id)
        fetched = transcript.fetch()
    except Exception as exc:
        raise RuntimeError(describe_transcript_error(video_id, exc)) from exc

    if hasattr(fetched, "to_raw_data"):
        raw_entries = fetched.to_raw_data()
    else:
        raw_entries = [
            {
                "text": getattr(item, "text", ""),
                "start": getattr(item, "start", 0.0),
                "duration": getattr(item, "duration", 0.0),
            }
            for item in fetched
        ]

    segments = normalize_transcript_entries(raw_entries)
    if not segments:
        raise RuntimeError(f"The transcript for video {video_id} was empty.")

    transcript_info = {
        "language": getattr(transcript, "language", None),
        "language_code": getattr(transcript, "language_code", None),
        "is_generated": getattr(transcript, "is_generated", None),
    }
    return segments, transcript_info


def describe_transcript_error(video_id: str, exc: Exception) -> str:
    name = exc.__class__.__name__
    if name == "TranscriptsDisabled":
        return f"No usable captions are available for video {video_id} because transcripts are disabled."
    if name == "NoTranscriptFound":
        return f"No usable captions were found for video {video_id}."
    if name == "VideoUnavailable":
        return f"Video {video_id} is unavailable or private."
    if name == "VideoUnplayable":
        return f"Video {video_id} is unplayable because of playback restrictions."
    if name == "AgeRestricted":
        return f"Video {video_id} is age-restricted and its transcript could not be retrieved."
    if name == "InvalidVideoId":
        return f"Video {video_id} is not a valid YouTube video ID."
    message = str(exc).strip()
    if message:
        return f"Could not retrieve a transcript for video {video_id}: {message}"
    return f"Could not retrieve a transcript for video {video_id}."


def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fetch_video_metadata(url: str, video_id: str) -> dict:
    metadata = {
        "title": f"YouTube video {video_id}",
        "channel": None,
        "channel_url": None,
        "upload_date_raw": None,
        "publish_date": None,
        "duration_seconds": None,
    }
    if yt_dlp is None:
        return metadata

    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        LOGGER.warning(f"    Metadata enrichment via yt-dlp failed: {exc}")
        return metadata

    upload_date = info.get("upload_date")
    metadata["title"] = info.get("title") or metadata["title"]
    metadata["channel"] = info.get("channel") or info.get("uploader")
    metadata["channel_url"] = info.get("uploader_url") or info.get("channel_url")
    metadata["upload_date_raw"] = upload_date
    metadata["publish_date"] = format_upload_date(upload_date)
    metadata["duration_seconds"] = info.get("duration")
    return metadata


def format_upload_date(upload_date: str | None) -> str | None:
    if not upload_date:
        return None
    if re.fullmatch(r"\d{8}", upload_date):
        return f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
    return upload_date


def transcript_lines(segments: Sequence[TranscriptSegment]) -> list[str]:
    return [f"[{segment.timestamp}] {segment.text}" for segment in segments]


def group_lines_by_tokens(lines: Sequence[str], encoder, token_limit: int) -> list[str]:
    chunks: list[str] = []
    current_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = count_tokens(line + "\n", encoder)
        if current_lines and current_tokens + line_tokens > token_limit:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_tokens = line_tokens
        else:
            current_lines.append(line)
            current_tokens += line_tokens

    if current_lines:
        chunks.append("\n".join(current_lines))
    return chunks


def group_texts_by_tokens(texts: Sequence[str], encoder, token_limit: int) -> list[list[str]]:
    groups: list[list[str]] = []
    current_group: list[str] = []
    current_tokens = 0

    for text in texts:
        block = text.strip()
        block_tokens = count_tokens(block, encoder) + 8
        if current_group and current_tokens + block_tokens > token_limit:
            groups.append(current_group)
            current_group = [block]
            current_tokens = block_tokens
        else:
            current_group.append(block)
            current_tokens += block_tokens

    if current_group:
        groups.append(current_group)
    return groups


def extract_usage(response) -> UsageTotals:
    usage = getattr(response, "usage", None)
    if usage is None:
        return UsageTotals()
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or (input_tokens + output_tokens))
    return UsageTotals(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def extract_response_text(response) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", None) != "output_text":
                continue
            text_value = getattr(content, "text", None)
            if isinstance(text_value, str):
                parts.append(text_value)
            elif hasattr(text_value, "value"):
                parts.append(text_value.value)
    return "\n".join(part.strip() for part in parts if part and part.strip()).strip()


def strip_markdown_fences(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def call_model(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    reasoning_effort: str,
    verbosity: str,
    max_output_tokens: int,
) -> tuple[str, UsageTotals]:
    response = client.responses.create(
        model=model,
        instructions=system_prompt,
        input=user_prompt,
        reasoning={"effort": reasoning_effort},
        text={"verbosity": verbosity},
        max_output_tokens=max_output_tokens,
    )
    text = strip_markdown_fences(extract_response_text(response))
    if not text:
        raise RuntimeError("The OpenAI response did not contain any text output.")
    return text, extract_usage(response)


def build_chunk_prompt(metadata: VideoMetadata, chunk_text: str, chunk_index: int, chunk_count: int) -> str:
    return f"""Prepare source-grounded intermediate notes for a YouTube transcript chunk.

Video metadata:
- Title: {metadata.display_title}
- Channel: {metadata.channel or "Unknown"}
- URL: {metadata.original_url}
- Transcript language: {metadata.transcript_language or "Unknown"}
- Chunk: {chunk_index} of {chunk_count}

Use only the transcript chunk below.
Do not write the final report yet.
Keep the notes compact, faithful, and useful for later synthesis.

Return valid Markdown with these sections in this exact order:
### Chunk Summary
### Important Takeaways
### Timestamped Notes

Rules:
- `### Chunk Summary` should use as many dense bullets as needed to capture all materially useful ideas from this chunk. Do not pad with setup, repetition, or trivial examples.
- `### Important Takeaways` should contain every distinct takeaway from this chunk that would materially change what a careful reader understands, decides, or does. Longer chunks may yield more takeaways than shorter ones. If none are present, write `- No materially useful takeaways beyond context-setting in this chunk.`
- `### Timestamped Notes` should use bullets in the format `- [HH:MM:SS] point`.
- Merge overlapping takeaways instead of splitting one idea into multiple bullets.
- Do not create standalone bullets for anecdotes, repetition, or examples unless they add a new principle, tactic, warning, or constraint.
- Preserve uncertainty and caveats instead of smoothing them away.

Transcript chunk:
{chunk_text}
"""


def build_reduction_prompt(group_text: str, round_index: int, group_index: int, group_count: int) -> str:
    return f"""Merge these intermediate notes from the same YouTube video into a tighter source-grounded note set.

This is reduction round {round_index}, group {group_index} of {group_count}.
Use only the notes below.
Do not invent missing context.

Return valid Markdown with these sections in this exact order:
### Combined Summary
### Combined Important Takeaways
### Combined Timeline

Rules:
- Remove repetition.
- Keep all materially useful takeaways that survive deduplication. Do not pad with low-value bullets.
- Merge bullets that differ only by example or phrasing, but keep genuinely distinct takeaways separate.
- Preserve the strongest caveats, constraints, and uncertainties.
- Keep timestamps when they anchor key claims or topic shifts.
- `### Combined Timeline` should use bullets in the format `- [HH:MM:SS] point`.

Notes to merge:
{group_text}
"""


def build_final_prompt(metadata: VideoMetadata, consolidated_notes: str) -> str:
    return f"""Create the final Markdown body for a YouTube video summary.

Video metadata:
- Title: {metadata.display_title}
- Channel: {metadata.channel or "Unknown"}
- URL: {metadata.original_url}
- Published: {metadata.publish_date or "Unknown"}
- Duration: {metadata.duration_display or "Unknown"}
- Transcript language: {metadata.transcript_display}

Use only the notes below.
Write in English.

Return valid Markdown with these sections in this exact order:
## Executive Brief
## Important Takeaways
## Key Moments
## Research Notes

Requirements:
- `## Executive Brief`: keep it short and high-signal. Use a short paragraph or a few concise bullets, whichever best communicates the main point and why it matters. Use as much detail as necessary, but no more.
- `## Important Takeaways`: bullets only. Include all materially useful takeaways from the video that would change what a careful reader understands, decides, or does. The number of bullets should scale with the actual content density of the video. Longer, denser videos may have more takeaways than shorter ones. Use as many bullets as necessary, but no more. If none are present, write `- No materially useful takeaways were stated beyond general context.`
- `## Key Moments`: use as many bullets as needed to cover the major moments or topic shifts that actually matter, using the format `- [HH:MM:SS] short label - why it matters`.
- `## Research Notes`: concise bullets or short paragraphs capturing nuance, caveats, examples, definitions, and supporting detail not already covered.
- Merge overlapping takeaways and keep the list tight. Do not pad with fluff, introductions, repetition, or low-value examples.
- Do not add a title section, metadata section, or notable quotes section.
- Do not invent facts or quotes.
- If the transcript appears incomplete or unclear, say so briefly.

Consolidated notes:
{consolidated_notes}
"""


def summarize_transcript(
    client: OpenAI,
    model: str,
    system_prompt: str,
    metadata: VideoMetadata,
    segments: Sequence[TranscriptSegment],
    encoder,
) -> tuple[str, UsageTotals]:
    usage_totals = UsageTotals()
    chunks = group_lines_by_tokens(transcript_lines(segments), encoder, TRANSCRIPT_CHUNK_TOKEN_LIMIT)
    chunk_notes: list[str] = []

    LOGGER.info(f"    Transcript split into {len(chunks)} chunk(s).")
    for index, chunk in enumerate(chunks, start=1):
        LOGGER.info(f"    Summarizing chunk {index} of {len(chunks)}.")
        prompt = build_chunk_prompt(metadata, chunk, index, len(chunks))
        note_text, usage = call_model(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            reasoning_effort="low",
            verbosity="low",
            max_output_tokens=2_500,
        )
        usage_totals.add(usage)
        chunk_notes.append(note_text)

    consolidated_notes = reduce_notes_if_needed(
        client=client,
        model=model,
        system_prompt=system_prompt,
        notes=chunk_notes,
        encoder=encoder,
        usage_totals=usage_totals,
    )

    LOGGER.info("    Creating final report sections.")
    final_prompt = build_final_prompt(metadata, consolidated_notes)
    final_sections, usage = call_model(
        client=client,
        model=model,
        system_prompt=system_prompt,
        user_prompt=final_prompt,
        reasoning_effort="medium",
        verbosity="medium",
        max_output_tokens=4_500,
    )
    usage_totals.add(usage)
    return final_sections, usage_totals


def reduce_notes_if_needed(
    client: OpenAI,
    model: str,
    system_prompt: str,
    notes: list[str],
    encoder,
    usage_totals: UsageTotals,
) -> str:
    current_notes = notes[:]
    round_index = 1

    while len(current_notes) > 1 and count_tokens("\n\n".join(current_notes), encoder) > FINAL_NOTES_TOKEN_LIMIT:
        groups = group_texts_by_tokens(current_notes, encoder, NOTE_REDUCTION_TOKEN_LIMIT)
        LOGGER.info(
            f"    Reduction round {round_index}: "
            f"{len(current_notes)} note block(s) -> {len(groups)} group(s)."
        )
        if len(groups) == 1:
            break

        reduced_notes: list[str] = []
        for group_index, group in enumerate(groups, start=1):
            prompt = build_reduction_prompt(
                "\n\n".join(group),
                round_index=round_index,
                group_index=group_index,
                group_count=len(groups),
            )
            reduced_text, usage = call_model(
                client=client,
                model=model,
                system_prompt=system_prompt,
                user_prompt=prompt,
                reasoning_effort="medium",
                verbosity="low",
                max_output_tokens=2_500,
            )
            usage_totals.add(usage)
            reduced_notes.append(reduced_text)

        current_notes = reduced_notes
        round_index += 1

    return "\n\n".join(current_notes)


def find_existing_output(output_dir: Path, video_id: str) -> Path | None:
    flat_path = output_dir / f"{video_id}.md"
    if flat_path.is_file():
        return flat_path
    matches = sorted(path for path in output_dir.rglob(f"* - {video_id}.md") if path.is_file())
    if not matches:
        matches = sorted(path for path in output_dir.rglob(f"*{video_id}.md") if path.is_file())
    return matches[0] if matches else None


def build_output_directory_name(metadata: VideoMetadata) -> str:
    return sanitize_path_component(metadata.channel, fallback="Unknown uploader", max_length=120)


def build_output_filename(metadata: VideoMetadata) -> str:
    upload_date = metadata.upload_date_raw or "unknown_date"
    title = sanitize_path_component(metadata.title, fallback="YouTube video", max_length=180)
    duration = format_duration_for_filename(metadata.duration_seconds)
    return f"{upload_date} - {title} - {duration} - {metadata.video_id}.md"


def build_output_path(output_dir: Path, metadata: VideoMetadata) -> Path:
    return output_dir / build_output_directory_name(metadata) / build_output_filename(metadata)


def processed_video_ids_path() -> Path:
    return Path(__file__).with_name(PROCESSED_VIDEO_IDS_FILENAME)


def load_processed_video_ids() -> set[str]:
    registry_path = processed_video_ids_path()
    if not registry_path.exists():
        return set()

    try:
        lines = registry_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"Could not read processed video ID registry {registry_path}: {exc}") from exc

    return {line.strip() for line in lines if line.strip()}


def record_processed_video_id(processed_video_ids: set[str], video_id: str) -> None:
    if video_id in processed_video_ids:
        return

    registry_path = processed_video_ids_path()
    try:
        with registry_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{video_id}\n")
    except OSError as exc:
        raise RuntimeError(f"Could not update processed video ID registry {registry_path}: {exc}") from exc

    processed_video_ids.add(video_id)


def render_metadata_section(
    metadata: VideoMetadata,
    generation_timestamp: str,
    model: str,
) -> str:
    lines = [
        "## Metadata",
        f"- URL: {metadata.original_url}",
        f"- Video ID: {metadata.video_id}",
        f"- Channel: {metadata.channel or 'Unknown'}",
        f"- Channel URL: {metadata.channel_url or 'Unknown'}",
        f"- Published: {metadata.publish_date or 'Unknown'}",
        f"- Duration: {metadata.duration_display or 'Unknown'}",
        f"- Transcript: {metadata.transcript_display}",
        f"- Generated at: {generation_timestamp}",
        f"- Model: {model}",
    ]
    return "\n".join(lines)


def _yaml_str(value: str) -> str:
    if any(c in value for c in ':{}[],"\'|>&*!%#`@'):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return f'"{value}"'


def render_frontmatter(
    metadata: VideoMetadata,
    generation_timestamp: str,
    model: str,
) -> str:
    slug = build_url_slug(metadata)
    channel_slug = build_channel_slug(metadata.channel)

    iso_timestamp = generation_timestamp
    if "T" not in iso_timestamp:
        try:
            dt = datetime.strptime(generation_timestamp, "%Y-%m-%d %H:%M:%S")
            iso_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    lines = [
        "---",
        "schemaVersion: 1",
        f"title: {_yaml_str(metadata.display_title)}",
        f"videoId: {_yaml_str(metadata.video_id)}",
        f"slug: {_yaml_str(slug)}",
        f"sourceUrl: {_yaml_str(metadata.original_url)}",
        f"channel: {_yaml_str(metadata.channel or 'Unknown')}",
        f"channelSlug: {_yaml_str(channel_slug)}",
        f"channelUrl: {_yaml_str(metadata.channel_url or 'Unknown')}",
        f"publishDate: {_yaml_str(metadata.publish_date or 'Unknown')}",
        f"uploadDateRaw: {_yaml_str(metadata.upload_date_raw or 'unknown')}",
        f"durationSeconds: {metadata.duration_seconds if metadata.duration_seconds is not None else 'null'}",
        f"durationDisplay: {_yaml_str(metadata.duration_display or 'Unknown')}",
        f"transcriptLanguage: {_yaml_str(metadata.transcript_language or 'Unknown')}",
        f"transcriptLanguageCode: {_yaml_str(metadata.transcript_language_code or 'unknown')}",
        f"transcriptIsGenerated: {str(metadata.transcript_is_generated).lower() if metadata.transcript_is_generated is not None else 'null'}",
        f"generatedAt: {_yaml_str(iso_timestamp)}",
        f"model: {_yaml_str(model)}",
        "---",
    ]
    return "\n".join(lines)


def assemble_report(
    metadata: VideoMetadata,
    body_markdown: str,
    generation_timestamp: str,
    model: str,
) -> str:
    parts = [
        f"# {metadata.display_title}",
        "",
        render_metadata_section(metadata, generation_timestamp, model),
        "",
        strip_markdown_fences(body_markdown).strip(),
    ]
    return "\n".join(parts).rstrip() + "\n"


def assemble_astro_report(
    metadata: VideoMetadata,
    body_markdown: str,
    generation_timestamp: str,
    model: str,
) -> str:
    parts = [
        render_frontmatter(metadata, generation_timestamp, model),
        "",
        strip_markdown_fences(body_markdown).strip(),
    ]
    return "\n".join(parts).rstrip() + "\n"


def process_video(
    target: VideoTarget,
    current_index: int,
    total_videos: int,
    output_dir: Path,
    processed_video_ids: set[str],
    client: OpenAI | None,
    model: str,
    system_prompt: str,
    encoder,
    dry_run: bool,
    astro: bool = False,
) -> tuple[str, Path | None, UsageTotals]:
    LOGGER.info(f"Processing video {current_index}/{total_videos}: {target.canonical_url}")

    if target.video_id in processed_video_ids:
        LOGGER.info(
            f"Skipping {target.canonical_url} because {target.video_id} is already listed in "
            f"{processed_video_ids_path().name}."
        )
        return "skipped", None, UsageTotals()

    existing_output = find_existing_output(output_dir, target.video_id)
    if existing_output is not None:
        LOGGER.info(f"Skipping {target.canonical_url} because {existing_output.name} already exists.")
        record_processed_video_id(processed_video_ids, target.video_id)
        return "skipped", existing_output, UsageTotals()

    if dry_run:
        LOGGER.info(
            f"    Dry run: would fetch metadata and transcript, generate a summary, and write output "
            f"under {output_dir}/<uploader>/<upload_date> - <title> - <duration> - <id>.md"
        )
        return "dry_run", None, UsageTotals()

    metadata_payload = fetch_video_metadata(target.canonical_url, target.video_id)
    metadata = VideoMetadata(
        video_id=target.video_id,
        original_url=target.canonical_url,
        title=metadata_payload["title"],
        channel=metadata_payload["channel"],
        channel_url=metadata_payload["channel_url"],
        upload_date_raw=metadata_payload["upload_date_raw"],
        publish_date=metadata_payload["publish_date"],
        duration_seconds=metadata_payload["duration_seconds"],
    )

    LOGGER.info(f"    Video: {metadata.display_title} ({target.video_id})")
    segments, transcript_info = fetch_transcript(target.video_id)
    metadata.transcript_language = transcript_info.get("language")
    metadata.transcript_language_code = transcript_info.get("language_code")
    metadata.transcript_is_generated = transcript_info.get("is_generated")

    LOGGER.info(
        f"    Retrieved {len(segments)} transcript segment(s) in "
        f"{metadata.transcript_display}."
    )

    body_markdown, usage = summarize_transcript(
        client=client,
        model=model,
        system_prompt=system_prompt,
        metadata=metadata,
        segments=segments,
        encoder=encoder,
    )

    generation_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if astro:
        output_path = output_dir / f"{metadata.video_id}.md"
        report = assemble_astro_report(
            metadata=metadata,
            body_markdown=body_markdown,
            generation_timestamp=generation_timestamp,
            model=model,
        )
    else:
        output_path = build_output_path(output_dir, metadata)
        report = assemble_report(
            metadata=metadata,
            body_markdown=body_markdown,
            generation_timestamp=generation_timestamp,
            model=model,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    record_processed_video_id(processed_video_ids, target.video_id)

    LOGGER.info(
        "    Tokens used: "
        f"input={usage.input_tokens}, output={usage.output_tokens}, total={usage.total_tokens}"
    )
    LOGGER.info(f"    Wrote summary to {output_path}")
    return "processed", output_path, usage


def main() -> int:
    args = parse_args()
    configure_logging(args)
    load_repo_dotenv()

    output_dir = resolve_path(args.output_dir)
    processed_video_ids = load_processed_video_ids()
    system_prompt, system_prompt_path = load_system_prompt(args.system_prompt_file)

    client: OpenAI | None = None
    encoder = None

    if args.dry_run:
        LOGGER.info(
            "Dry run enabled: skipping metadata fetch, transcript fetch, OpenAI summarization, "
            "report writes, and processed-ID updates."
        )
        if not output_dir.exists():
            LOGGER.info(
                f"Dry run note: output directory does not exist yet and would be created during a real run: "
                f"{output_dir}"
            )
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing OPENAI_API_KEY environment variable.")
        output_dir.mkdir(parents=True, exist_ok=True)
        encoder = get_encoder(args.model)
        client = OpenAI(api_key=api_key)

    if getattr(args, "playlist_url", None) and yt_dlp is None:
        raise RuntimeError(
            "yt-dlp is required for playlist mode but is not installed. "
            "Install it with: pip install yt-dlp"
        )

    LOGGER.info(f"Using model: {args.model}")
    LOGGER.info(f"Using system prompt: {system_prompt_path}")
    LOGGER.debug(
        f"Loaded {len(processed_video_ids)} processed video IDs from "
        f"{processed_video_ids_path()}"
    )
    if not args.dry_run and yt_dlp is None and not getattr(args, "playlist_url", None):
        LOGGER.info("Metadata enrichment note: optional package yt-dlp is not installed.")

    targets, initial_failures = build_targets(args)

    processed_count = 0
    skipped_count = 0
    dry_run_count = 0
    usage_totals = UsageTotals()
    failures = initial_failures[:]
    total_videos = len(targets)

    for index, target in enumerate(targets, start=1):
        try:
            status, _, usage = process_video(
                target=target,
                current_index=index,
                total_videos=total_videos,
                output_dir=output_dir,
                processed_video_ids=processed_video_ids,
                client=client,
                model=args.model,
                system_prompt=system_prompt,
                encoder=encoder,
                dry_run=args.dry_run,
                astro=args.astro,
            )
            usage_totals.add(usage)
            if status == "processed":
                processed_count += 1
            elif status == "dry_run":
                dry_run_count += 1
            else:
                skipped_count += 1
        except Exception as exc:
            failures.append(f"{target.canonical_url} -> {exc}")
            LOGGER.error(f"Failed to process {target.canonical_url}: {exc}")

    LOGGER.info("Run summary")
    LOGGER.info(f"- Processed: {processed_count}")
    if args.dry_run:
        LOGGER.info(f"- Would process: {dry_run_count}")
    LOGGER.info(f"- Skipped: {skipped_count}")
    LOGGER.info(f"- Failed: {len(failures)}")
    LOGGER.info(
        f"- Tokens: input={usage_totals.input_tokens}, "
        f"output={usage_totals.output_tokens}, total={usage_totals.total_tokens}"
    )

    if failures:
        LOGGER.error("Failures")
        for failure in failures:
            LOGGER.error(f"- {failure}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
