#!/usr/bin/env python3
"""
unified_translate_epub.py

Usage:
    # Live translation mode (default):
    python translate_epub.py -i input.epub -o output.epub --system_prompt_file PATH [--model MODEL] [--chunk_size N]
    # Alternatively, place a system_prompt.txt next to this script and omit --system_prompt_file.

    # Injection mode: use pretranslated HTML files to rebuild EPUB:
    python translate_epub.py -i input.epub -o output.epub --translated_dir path/to/html_dir

Options:
    -i INPUT_EPUB, --input_epub INPUT_EPUB        Path to the input EPUB file (required)
    -o OUTPUT_EPUB, --output_epub OUTPUT_EPUB     Path for the output EPUB file (required)
    --model MODEL                                 OpenAI model to use for translation (default: gpt-5)
    --chunk_size N                                Maximum tokens per translation chunk (default: 100000)
    --translated_dir DIR                          Directory with pretranslated HTML files to inject (optional)
    --system_prompt_file PATH                     Path to system prompt file (required if no system_prompt.txt next to script)
    --provider CHOICE                             Which API provider to use: openai or google (default: openai)

Environment:
    Set OPENAI_API_KEY to your OpenAI API key (for live mode).

This script modifies an EPUB in-place, replacing the content of each XHTML item with either:
  - A live translation via OpenAI API (English -> Slovenian), or
  - Injected pretranslated HTML files, merging their <body> content into the original XHTML structure.

All other files, folders, metadata, and assets (images, CSS, fonts) are preserved exactly.
"""
import os
import sys
import argparse
import re
from pathlib import Path

import openai
from openai import BadRequestError
import requests
import time
from ebooklib import epub
from ebooklib.epub import EpubHtml, EpubException
from bs4 import BeautifulSoup
import tiktoken
import zipfile
from dotenv import load_dotenv


def parse_args():
    parser = argparse.ArgumentParser(description="Translate or inject translations into an EPUB.")
    parser.add_argument("-i", "--input_epub", required=True, help="Path to the input EPUB file")
    parser.add_argument("-o", "--output_epub", required=True, help="Path for the output EPUB file")
    parser.add_argument("--model", default="gpt-5", help="OpenAI model for live translation")
    parser.add_argument("--chunk_size", type=int, default=100000, help="Max tokens per translation chunk")
    parser.add_argument("--translated_dir", help="Directory containing pretranslated HTML files to inject")
    parser.add_argument("--system_prompt_file", help="Path to a system prompt text file (required if system_prompt.txt is absent)")
    parser.add_argument("--provider", choices=["openai", "google"], default="openai", help="Which API provider to use: openai or google")
    return parser.parse_args()


def load_system_prompt(path: Path) -> str:
    """Load a mandatory system prompt from disk or exit with an error."""
    prompt_path = Path(path)
    if not prompt_path.exists():
        print(f"[Error] System prompt file is required but was not found at {prompt_path}.")
        print("        Provide one via --system_prompt_file or place system_prompt.txt next to this script.")
        sys.exit(1)
    try:
        content = prompt_path.read_text(encoding='utf-8', errors='ignore').strip()
    except OSError as exc:
        print(f"[Error] Could not read system prompt file {prompt_path}: {exc}")
        sys.exit(1)
    if not content:
        print(f"[Error] System prompt file {prompt_path} is empty; please provide content.")
        sys.exit(1)
    print(f"[Info] Loaded system prompt from {prompt_path}")
    return content


def chunk_html(html, encoder, max_tokens):
    soup = BeautifulSoup(html, 'html.parser')
    body = soup.body or soup
    blocks = [str(tag) for tag in body.find_all(['p', 'h1','h2','h3','h4','h5','li','blockquote'])]
    if not blocks:
        blocks = [html]
    chunks = []
    curr, curr_tokens = '', 0
    for block in blocks:
        size = len(encoder.encode(block))
        if size > max_tokens:
            chunks.append(block)
            continue
        if curr_tokens + size > max_tokens:
            if curr:
                chunks.append(curr)
            curr, curr_tokens = block, size
        else:
            curr += block
            curr_tokens += size
    if curr:
        chunks.append(curr)
    return chunks


def translate_chunk(chunk, model, system_prompt: str):
    """Translate an HTML chunk using the provided system prompt (required)."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": chunk})
    if openai.api_base.startswith("https://generativelanguage.googleapis.com"):
        url = f"{openai.api_base}/chat/completions"
        # Authenticate via Bearer header; send model in the JSON body
        headers = {
            "Authorization": f"Bearer {openai.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"model": model, "messages": messages}
        max_retries = 3
        backoff_base = 1
        for attempt in range(1, max_retries + 1):
            resp = requests.post(url, headers=headers, json=payload)
            try:
                resp.raise_for_status()
                data = resp.json()
                # Attempt to extract translated content
                content = data["choices"][0]["message"]["content"]
                return content
            except requests.exceptions.HTTPError:
                print(f"Google endpoint error (attempt {attempt}/{max_retries}): {resp.status_code}\n{resp.text}")
            except (KeyError, TypeError) as e:
                # Unexpected response structure
                print(f"Google endpoint unexpected response (attempt {attempt}/{max_retries}): {data}")
            # Last attempt: raise error
            if attempt == max_retries:
                # Re-raise the last exception
                raise
            # Otherwise, backoff and retry
            sleep_time = backoff_base * 2 ** (attempt - 1)
            print(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)
    resp = openai.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content


def main():
    args = parse_args()
    input_epub = args.input_epub
    output_epub = args.output_epub
    html_dir = Path(args.translated_dir) if args.translated_dir else None
    default_prompt_path = Path(__file__).with_name("system_prompt.txt")
    prompt_path = Path(args.system_prompt_file) if args.system_prompt_file else default_prompt_path
    custom_system_prompt = load_system_prompt(prompt_path)
    # Read original EPUB as ZIP
    with zipfile.ZipFile(input_epub, 'r') as zin:
        infos = zin.infolist()
        namelist = [info.filename for info in infos]
        data_map = {info.filename: zin.read(info.filename) for info in infos}
    # Determine mode
    inject = bool(html_dir)
    # Collect XHTML/HTML files
    html_files = [fn for fn in namelist if fn.lower().endswith(('.xhtml', '.html'))]
    total = len(html_files)
    print(f"Found {total} XHTML/HTML files to process")
    # Prepare API for live mode
    if not inject:
        load_dotenv()
        if args.provider == "google":
            # Use Google Gemini endpoint and env var
            key = os.getenv("GOOGLE_API_KEY")
            if not key:
                print("Error: GOOGLE_API_KEY not set for google provider")
                sys.exit(1)
            openai.api_key = key
            openai.api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        else:
            # Default to OpenAI provider
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                print("Error: OPENAI_API_KEY not set for openai provider")
                sys.exit(1)
            openai.api_key = key
        try:
            encoder = tiktoken.encoding_for_model(args.model)
        except KeyError:
            print(f"Warning: unknown model {args.model}, using cl100k_base encoding.")
            encoder = tiktoken.get_encoding('cl100k_base')
    # Process each XHTML/HTML file in order
    for idx, filename in enumerate(html_files, start=1):
        # add a new line before the print
        print()
        print(f"[{idx}/{total}] Processing {filename}")
        # Decode original content with fallback to ignore invalid bytes
        orig = data_map[filename].decode('utf-8', errors='ignore')
        # Find body tags
        m_open = re.search(r'<body[^>]*>', orig, flags=re.IGNORECASE)
        m_close = re.search(r'</body>', orig, flags=re.IGNORECASE)
        if not m_open or not m_close:
            print(f"  [!] Skipping: <body> tags not found")
            continue
        prefix = orig[:m_open.end()]
        suffix = orig[m_close.start():]
        #print(f"  Prefix len={len(prefix)} | Suffix len={len(suffix)}")
        if inject:
            stem = Path(filename).stem
            trans_file = html_dir / f"{stem}.html"
            if not trans_file.exists():
                print(f"  [!] Skipping: missing translation file {trans_file}")
                continue
            print(f"  [Inject] Using translated HTML from {trans_file}")
            trans_html = trans_file.read_text(encoding='utf-8', errors='ignore')
            m_o2 = re.search(r'<body[^>]*>', trans_html, flags=re.IGNORECASE)
            m_c2 = re.search(r'</body>', trans_html, flags=re.IGNORECASE)
            body_inner = trans_html[m_o2.end():m_c2.start()] if m_o2 and m_c2 else trans_html
        else:
            # Live translation with fallback
            inner = orig[m_open.end():m_close.start()]
            tokens = len(encoder.encode(inner))
            # Determine if we need to chunk first
            if tokens > args.chunk_size:
                print(f"  [Translate] Content tokens ({tokens}) exceed chunk_size ({args.chunk_size}), using chunked translation")
                parts = []
                for idx, chunk in enumerate(chunk_html(inner, encoder, args.chunk_size), start=1):
                    print(f"    Translating chunk {idx} of {len(chunk_html(inner, encoder, args.chunk_size))} ({len(chunk)} chars)")
                    parts.append(translate_chunk(chunk, args.model, custom_system_prompt))
                body_inner = ''.join(parts)
            else:
                try:
                    print(f"  [Translate] Translating full content ({tokens} tokens)")
                    body_inner = translate_chunk(inner, args.model, custom_system_prompt)
                    #print(body_inner)
                except BadRequestError as e:
                    msg = str(e)
                    if 'maximum context length' in msg or 'context length' in msg:
                        print("  [Warning] Context limit exceeded, falling back to chunked translation")
                        parts = []
                        for idx, chunk in enumerate(chunk_html(inner, encoder, args.chunk_size), start=1):
                            print(f"    Translating chunk {idx}/{len(chunk_html(inner, encoder, args.chunk_size))}")
                            parts.append(translate_chunk(chunk, args.model, custom_system_prompt))
                        body_inner = ''.join(parts)
                    else:
                        raise
        # Adjust image paths
        #body_inner = body_inner.replace('src="images/', 'src="../images/')
        # Rebuild content
        new_text = prefix + body_inner + suffix
        data_map[filename] = new_text.encode('utf-8')
    # Write new EPUB
    with zipfile.ZipFile(output_epub, 'w') as zout:
        # mimetype first
        if 'mimetype' in data_map:
            zout.writestr('mimetype', data_map['mimetype'], compress_type=zipfile.ZIP_STORED)
        for name in namelist:
            if name == 'mimetype': continue
            zout.writestr(name, data_map[name], compress_type=zipfile.ZIP_DEFLATED)
    print(f"Wrote translated EPUB to {output_epub}")

if __name__ == '__main__':
    main()
