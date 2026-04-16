# YouTube Summarizer CLI

> **Note:** For automated digest site content generation (YouTube channels, playlists, RSS feeds, daily digests), use the [digest-pipeline](https://github.com/zigamilek/digest-pipeline) instead. This standalone script remains useful for one-off summarization outside the pipeline.

Summarize YouTube videos into Markdown using the OpenAI API.

The script:
- accepts a single YouTube URL, an input file with multiple URLs, or a YouTube playlist URL
- fetches YouTube captions first and fails clearly when captions are unavailable
- writes one Markdown summary per video
- uses `gpt-5.4` by default
- loads its default system prompt from `system_prompt.md`
- logs to the console and to a local log file with `INFO` verbosity by default

## Output

Default output directory:

`/Users/zigamilek/Library/CloudStorage/Dropbox/Zigec/AI/YouTube video summaries`

Default filename pattern:

`<uploader>/<upload_date> - <title> - <[Xh]Ym duration> - <videoId>.md`

Examples:

- `Google for Developers/20130410 - YouTube Developers Live Embedded Web Player Customization - 22m - M7lc1UVf-VE.md`
- `Unknown uploader/unknown_date - YouTube video - unknown_duration - dQw4w9WgXcQ.md` when metadata cannot be fetched cleanly

The script sanitizes uploader and title names to stay filesystem-safe.
It treats `videoId` as the deduplication key and skips a video if a matching summary file for that ID already exists anywhere under the output directory.
It also keeps a persistent processed-ID registry at `processed_video_ids.txt` next to the script (gitignored), so future runs can skip videos that were already summarized regardless of the output directory used.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional metadata enrichment (required for playlist mode):

```bash
pip install yt-dlp
```

## Environment

The script looks upward from its own directory for a `.env` file and expects:

```env
OPENAI_API_KEY=your_api_key_here
```

## Usage

Single video:

```bash
python3 "youtube_summarizer.py" --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Batch file:

```bash
python3 "youtube_summarizer.py" --input-file "/path/to/youtube-links.txt"
```

Dry run:

```bash
python3 "youtube_summarizer.py" --input-file "/path/to/youtube-links.txt" --dry-run
```

Override output directory:

```bash
python3 "youtube_summarizer.py" --url "https://youtu.be/dQw4w9WgXcQ" --output-dir "/tmp/youtube-summaries"
```

Override model:

```bash
python3 "youtube_summarizer.py" --url "https://youtu.be/dQw4w9WgXcQ" --model "gpt-5.4"
```

Override log verbosity:

```bash
python3 "youtube_summarizer.py" --url "https://youtu.be/dQw4w9WgXcQ" --log "DEBUG"
```

Override the default system prompt file:

```bash
python3 "youtube_summarizer.py" --url "https://youtu.be/dQw4w9WgXcQ" --system-prompt-file "/path/to/alternate_prompt.md"
```

Public playlist:

```bash
python3 "youtube_summarizer.py" --playlist-url "https://www.youtube.com/playlist?list=PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH"
```

Private playlist (public videos) using browser cookies:

```bash
python3 "youtube_summarizer.py" \
  --playlist-url "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxx" \
  --cookies-from-browser "firefox"
```

Private playlist using a cookies file:

```bash
python3 "youtube_summarizer.py" \
  --playlist-url "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxx" \
  --cookies-file "/path/to/cookies.txt"
```

Playlist with Astro output for the digest site:

```bash
python3 "youtube_summarizer.py" \
  --playlist-url "https://www.youtube.com/playlist?list=PLRqwX-V7Uu6ZiZxtDDRCi6uhfTH4FilpH" \
  --output-dir "/path/to/digest/src/content/youtube-video-summaries" \
  --astro
```

Astro output for the digest site:

```bash
python3 "youtube_summarizer.py" \
  --input-file "/path/to/youtube-links.txt" \
  --output-dir "/path/to/digest/src/content/youtube-video-summaries" \
  --astro
```

When `--astro` is set, the script emits YAML frontmatter instead of `# Title` and `## Metadata`, and uses flat `<videoId>.md` filenames instead of the nested uploader/date pattern.

You can combine overrides:

```bash
python3 "youtube_summarizer.py" \
  --input-file "/path/to/youtube-links.txt" \
  --output-dir "/tmp/youtube-summaries" \
  --model "gpt-5.4" \
  --log "INFO" \
  --dry-run \
  --system-prompt-file "/path/to/alternate_prompt.md"
```

## Input File Format

- one YouTube URL or bare video ID per line
- blank lines are ignored
- lines starting with `#` are ignored
- duplicate videos are skipped by `videoId`
- videos already listed in the output directory's `processed_video_ids.txt` file are skipped on future runs

Example:

```text
# English videos
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/3JZ_D3ELwOQ

# Bare IDs also work
M7lc1UVf-VE
```

## Report Structure

Each output file contains:

- `# Video Title`
- `## Metadata`
- `## Executive Brief`
- `## Important Takeaways`
- `## Key Moments`
- `## Research Notes`

The summary body is always written in English, even when the transcript language is different.
The `Important Takeaways` section uses an adaptive bullet count: longer, denser videos may have more takeaways than shorter ones, but the prompt is instructed not to pad with fluff.

## Playlist Support

The `--playlist-url` flag expands a YouTube playlist into individual video targets and processes them as a batch. This requires `yt-dlp`.

- **Public playlists** work out of the box.
- **Private playlists** whose videos are public can be accessed by supplying YouTube authentication cookies via `--cookies-from-browser` or `--cookies-file`. The cookies are only used for playlist enumeration; each video is then fetched and transcribed as a normal public video.
- Private playlist support is best-effort: YouTube cookies can expire or behave inconsistently across environments. If expansion fails, try refreshing cookies or exporting a fresh `cookies.txt` from an incognito session.

The `--cookies-file` and `--cookies-from-browser` flags are ignored when not using `--playlist-url`.

## Notes

- `yt-dlp` is optional for single-video and input-file modes but required for playlist mode. Without it, metadata enrichment may be less complete.
- When metadata is available, the report includes both the channel name and channel URL.
- The script uses YouTube captions only in this version. It does not download audio or run fallback transcription.
- If captions are disabled, missing, or restricted, the script reports the failure clearly and moves on in batch mode.
- Logging defaults to `INFO`, similar to your downloader scripts. The log file is written in the current working directory as `youtube_summarizer_<source>.log`.
- The processed-ID registry lives next to the script as `processed_video_ids.txt` (gitignored). If you ever want to reprocess a video, remove its ID from that file.
- `--dry-run` validates inputs and shows what would be processed, but it does not fetch transcripts, call OpenAI, write Markdown reports, or update `processed_video_ids.txt`.
