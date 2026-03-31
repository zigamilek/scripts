# YouTube Summarizer CLI

Summarize YouTube videos into Markdown using the OpenAI API.

The script:
- accepts either a single YouTube URL or an input file with multiple URLs
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
It also keeps a persistent processed-ID registry at `processed_video_ids.txt` inside the output directory, so future runs can skip videos that were already summarized before.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional metadata enrichment:

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

## Notes

- `yt-dlp` is optional. Without it, the script still works, but title/channel/duration metadata may be less complete.
- When metadata is available, the report includes both the channel name and channel URL.
- The script uses YouTube captions only in this version. It does not download audio or run fallback transcription.
- If captions are disabled, missing, or restricted, the script reports the failure clearly and moves on in batch mode.
- Logging defaults to `INFO`, similar to your downloader scripts. The log file is written in the current working directory as `youtube_summarizer_<source>.log`.
- The processed-ID registry lives in the chosen output directory. If you ever want to reprocess a video, remove its ID from `processed_video_ids.txt` or use a different output directory.
- `--dry-run` validates inputs and shows what would be processed, but it does not fetch transcripts, call OpenAI, write Markdown reports, or update `processed_video_ids.txt`.
