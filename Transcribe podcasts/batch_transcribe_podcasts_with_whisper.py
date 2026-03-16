#!/usr/bin/env python3

"""
Batch Transcription Script

Dependencies:
    pip install torch tqdm openai-whisper

Usage:
    python batch_transcribe_podcasts_with_whisper.py /path/to/input \
        --model medium.en \
        --output-folder /path/to/output \
        --language English \
        --extensions .mp3 .wav \
        --continue-on-error \
        --verbose

Examples:
    python batch_transcribe_podcasts_with_whisper.py ~/podcasts --verbose
"""

import os
import argparse
import logging
import json
from pathlib import Path

import torch
import whisper
from tqdm import tqdm

TRANSCRIBED_FILENAME = "already_transcribed.json"

# Setup logging configuration based on verbosity flag
def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        level=level
    )

# Load the set of already-transcribed files from a JSON bookkeeper
def load_transcribed(input_folder: Path) -> set:
    path = input_folder / TRANSCRIBED_FILENAME
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

# Save the updated set of transcribed files to JSON

def save_transcribed(input_folder: Path, transcribed: set):
    path = input_folder / TRANSCRIBED_FILENAME
    with path.open("w", encoding="utf-8") as f:
        json.dump(sorted(transcribed), f, indent=2)

# Recursively find audio files matching given extensions, skipping output folders
def find_audio_files(input_folder: Path, extensions: list[str]) -> list[Path]:
    exts = {e.lower() for e in extensions}
    files = []
    for p in input_folder.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts and "transcriptions" not in p.parts:
            files.append(p)
    return files

# Transcribe a single file using Whisper model
def transcribe_file(model, file_path: Path, language: str, use_fp16: bool) -> str:
    result = model.transcribe(str(file_path), language=language, fp16=use_fp16, verbose=False)
    return result.get("text", "")

# Write transcription text to disk in desired output folder
def write_transcription(file_path: Path, text: str, output_folder: Path) -> Path:
    output_folder.mkdir(parents=True, exist_ok=True)
    out_file = output_folder / f"{file_path.stem}-transcription.txt"
    with out_file.open("w", encoding="utf-8") as f:
        f.write(text)
    return out_file

# Entry point
def main():
    parser = argparse.ArgumentParser(description="Batch transcribe audio files with Whisper")
    parser.add_argument("input_folder", type=Path, help="Folder with audio files")
    parser.add_argument("--model", default="medium.en", help="Whisper model name")
    parser.add_argument("--output-folder", type=Path, help="Directory to save all transcripts. If not set, uses <audio_file_parent>/transcriptions")
    parser.add_argument("--language", default="English", help="Language for transcription")
    parser.add_argument("--extensions", nargs="+", default=[".mp3"], help="Audio file extensions to include")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue processing files after errors")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logging.info("Loading Whisper model: %s", args.model)
    use_fp16 = torch.cuda.is_available()
    model = whisper.load_model(args.model)

    processed = load_transcribed(args.input_folder)
    files = find_audio_files(args.input_folder, args.extensions)
    logging.info("Found %d files to process", len(files))

    for file in tqdm(files, desc="Transcribing"):  
        rel = str(file.relative_to(args.input_folder))
        if rel in processed:
            logging.debug("Skipping already transcribed %s", rel)
            continue
        try:
            text = transcribe_file(model, file, args.language, use_fp16)
            out_dir = args.output_folder or (file.parent / "transcriptions")
            out_file = write_transcription(file, text, out_dir)
            logging.info("Wrote transcription to %s", out_file)
            processed.add(rel)
            save_transcribed(args.input_folder, processed)
        except Exception as e:
            logging.error("Error processing %s: %s", file, e)
            if not args.continue_on_error:
                raise

    logging.info("Batch transcription completed.")

if __name__ == "__main__":
    main()