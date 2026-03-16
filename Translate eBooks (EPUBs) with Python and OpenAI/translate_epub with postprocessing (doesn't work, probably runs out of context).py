#!/usr/bin/env python3
"""
unified_translate_epub.py

Usage:
    # Translate then postprocess mode (default):
    python translate_epub.py -i input.epub -o output.epub --mode translate [--model MODEL] [--chunk_size N] [--instructions TEXT]

    # Injection mode: use pretranslated HTML files to rebuild EPUB (then postprocess):
    python translate_epub.py -i input.epub -o output.epub --translated_dir path/to/html_dir --mode translate

    # Postprocess-only mode: fix inconsistencies in an already-translated EPUB (requires --reference_epub):
    python translate_epub.py -i translated_input.epub -o fixed_output.epub --mode postprocess-only --reference_epub original.epub

Options:
    -i INPUT_EPUB, --input_epub INPUT_EPUB        Path to the input EPUB file (for translate mode) or the already-translated EPUB (for postprocess-only mode) (required)
    -o OUTPUT_EPUB, --output_epub OUTPUT_EPUB     Path for the output EPUB file (required)
    --model MODEL                                 OpenAI model to use for translation (default: gpt-5)
    --chunk_size N                                Maximum tokens per translation chunk (default: 2000)
    --translated_dir DIR                          Directory with pretranslated HTML files to inject (optional, only in translate mode)
    --instructions TEXT                           Additional instructions for the translator (e.g. glossary or style overrides)
    --provider CHOICE                             Which API provider to use: openai or google (default: openai)
    --mode MODE                                   Operation mode: translate (translate then postprocess) or postprocess-only (fix inconsistencies only)
    --reference_epub REF_EPUB                     Path to the original untranslated EPUB for reference (required in postprocess-only mode)

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
import json
from dotenv import load_dotenv


def load_repo_dotenv():
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


load_repo_dotenv()


def parse_args():
    parser = argparse.ArgumentParser(description="Translate or inject translations into an EPUB.")
    parser.add_argument("-i", "--input_epub", required=True, help="Path to the input EPUB file")
    parser.add_argument("-o", "--output_epub", required=True, help="Path for the output EPUB file")
    parser.add_argument("--model", default="gpt-5", help="OpenAI model for live translation")
    parser.add_argument("--chunk_size", type=int, default=100000, help="Max tokens per translation chunk")
    parser.add_argument("--translated_dir", help="Directory containing pretranslated HTML files to inject")
    parser.add_argument("--instructions", help="Additional instructions for the translator")
    parser.add_argument("--provider", choices=["openai", "google"], default="openai", help="Which API provider to use: openai or google")
    parser.add_argument("--mode", choices=["translate", "postprocess-only"], default="translate", help="Operation mode: translate (translate then postprocess) or postprocess-only (fix inconsistencies on existing translations)")
    parser.add_argument("--reference_epub", help="Path to the original untranslated EPUB for reference in postprocessing (required in postprocess-only mode)")
    return parser.parse_args()


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


def translate_chunk(chunk, model, instructions=None):
    """Translate an HTML chunk from English to Slovenian with optional custom instructions."""
    system_prompt = (
        "You are a translator that translates children books (ages roughly 7 to 18) "
        "from English to Slovenian. The content you get is HTML content. "
        "Preserve all HTML tags and attributes and return only the translated HTML."
    )
    messages = [{"role": "system", "content": system_prompt}]
    if instructions:
        messages.append({"role": "system", "content": instructions})
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


def fix_inconsistencies(data_map, html_files, args, reference_map=None):
    print("[Postprocess] Fixing inconsistencies across all translated chapters")
    chapters = []
    for filename in html_files:
        orig = data_map[filename].decode('utf-8', errors='ignore')
        m_open = re.search(r'<body[^>]*>', orig, flags=re.IGNORECASE)
        m_close = re.search(r'</body>', orig, flags=re.IGNORECASE)
        if not m_open or not m_close:
            continue
        prefix = orig[:m_open.end()]
        suffix = orig[m_close.start():]
        body_inner = orig[m_open.end():m_close.start()]
        # extract original untranslated body if reference provided
        if reference_map and filename in reference_map:
            ref_html = reference_map[filename].decode('utf-8', errors='ignore')
            m_o_ref = re.search(r'<body[^>]*>', ref_html, flags=re.IGNORECASE)
            m_c_ref = re.search(r'</body>', ref_html, flags=re.IGNORECASE)
            orig_body = ref_html[m_o_ref.end():m_c_ref.start()] if m_o_ref and m_c_ref else ref_html
        else:
            orig_body = None
        chapters.append({'filename': filename, 'prefix': prefix, 'suffix': suffix, 'body': body_inner, 'orig_body': orig_body})
    combined = ''
    for chap in chapters:
        if chap['orig_body'] is not None:
            combined += f"<!-- ORIGINAL CHAPTER {chap['filename']} -->\n{chap['orig_body']}\n"
        combined += f"<!-- TRANSLATED CHAPTER {chap['filename']} -->\n{chap['body']}\n"
    system_prompt = (
        "You are a translator and editor ensuring consistency across a book translation. "
        "Given all chapters together, fix inconsistencies in style, tone, and terminology. "
        "Preserve HTML tags. Return a JSON mapping filenames to their corrected inner HTML content. "
        "Output MUST be EXACTLY a JSON object mapping filenames to their corrected inner HTML, with no additional text or formatting."
    )
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": combined}]
    # Retry API call and JSON parsing up to 3 times
    max_retries = 3
    backoff_base = 1
    for attempt in range(1, max_retries + 1):
        try:
            # Send prompt to API (support OpenAI and Google providers)
            if openai.api_base.startswith("https://generativelanguage.googleapis.com"):
                url = f"{openai.api_base}/chat/completions"
                headers = {"Authorization": f"Bearer {openai.api_key}", "Content-Type": "application/json"}
                payload = {"model": args.model, "messages": messages}
                resp_http = requests.post(url, headers=headers, json=payload)
                resp_http.raise_for_status()
                data = resp_http.json()
                content = data["choices"][0]["message"]["content"]
            else:
                resp = openai.chat.completions.create(model=args.model, messages=messages)
                content = resp.choices[0].message.content
            # Attempt to parse JSON
            fixed = json.loads(content)
            break
        except Exception as e:
            err_name = type(e).__name__
            print(f"Postprocess error (attempt {attempt}/{max_retries}) - {err_name}: {e}")
            if attempt == max_retries:
                print("Raw postprocess response:")
                try:
                    print(content)
                except:
                    pass
                sys.exit(1)
            sleep_time = backoff_base * 2 ** (attempt - 1)
            print(f"Retrying postprocess in {sleep_time} seconds...")
            time.sleep(sleep_time)
    for chap in chapters:
        filename = chap['filename']
        if filename in fixed:
            new_text = chap['prefix'] + fixed[filename] + chap['suffix']
            data_map[filename] = new_text.encode('utf-8')
        else:
            print(f"  [Warning] No fixed content for {filename}, keeping original")
    print("[Postprocess] Completed fixing inconsistencies")


def main():
    args = parse_args()
    input_epub = args.input_epub
    output_epub = args.output_epub
    html_dir = Path(args.translated_dir) if args.translated_dir else None
    # Read original EPUB as ZIP
    with zipfile.ZipFile(input_epub, 'r') as zin:
        infos = zin.infolist()
        namelist = [info.filename for info in infos]
        data_map = {info.filename: zin.read(info.filename) for info in infos}
    # Preserve original EPUB content for reference if needed
    orig_data_map = dict(data_map)
    # Determine mode and inject flag
    inject = bool(html_dir)
    mode = args.mode
    ref_epub = args.reference_epub
    # In postprocess-only mode, reference EPUB must be provided
    if mode == 'postprocess-only' and not ref_epub:
        print("Error: --reference_epub is required in postprocess-only mode")
        sys.exit(1)
    # Load reference EPUB if provided, otherwise use original EPUB only in translate mode
    if ref_epub:
        with zipfile.ZipFile(ref_epub, 'r') as zref:
            ref_infos = zref.infolist()
            reference_map = {info.filename: zref.read(info.filename) for info in ref_infos}
    elif mode == 'translate':
        reference_map = orig_data_map
    else:
        reference_map = None

    # Prepare API for live or postprocess
    if not inject:
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
    # Collect XHTML/HTML files
    html_files = [fn for fn in namelist if fn.lower().endswith(('.xhtml', '.html'))]
    total = len(html_files)
    print(f"Found {total} XHTML/HTML files to process")

    if mode == 'postprocess-only':
        fix_inconsistencies(data_map, html_files, args, reference_map)
        # Write EPUB
        with zipfile.ZipFile(output_epub, 'w') as zout:
            if 'mimetype' in data_map:
                zout.writestr('mimetype', data_map['mimetype'], compress_type=zipfile.ZIP_STORED)
            for name in namelist:
                if name == 'mimetype': continue
                zout.writestr(name, data_map[name], compress_type=zipfile.ZIP_DEFLATED)
        print(f"Wrote EPUB to {output_epub}")
        return

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
                    parts.append(translate_chunk(chunk, args.model, args.instructions))
                body_inner = ''.join(parts)
            else:
                try:
                    print(f"  [Translate] Translating full content ({tokens} tokens)")
                    body_inner = translate_chunk(inner, args.model, args.instructions)
                    #print(body_inner)
                except BadRequestError as e:
                    msg = str(e)
                    if 'maximum context length' in msg or 'context length' in msg:
                        print("  [Warning] Context limit exceeded, falling back to chunked translation")
                        parts = []
                        for idx, chunk in enumerate(chunk_html(inner, encoder, args.chunk_size), start=1):
                            print(f"    Translating chunk {idx}/{len(chunk_html(inner, encoder, args.chunk_size))}")
                            parts.append(translate_chunk(chunk, args.model, args.instructions))
                        body_inner = ''.join(parts)
                    else:
                        raise
        # Adjust image paths
        #body_inner = body_inner.replace('src="images/', 'src="../images/')
        # Rebuild content
        new_text = prefix + body_inner + suffix
        data_map[filename] = new_text.encode('utf-8')

    # After translation or injection, if in translate mode perform postprocess
    if mode == 'translate':
        fix_inconsistencies(data_map, html_files, args, reference_map)

    # Write EPUB
    with zipfile.ZipFile(output_epub, 'w') as zout:
        if 'mimetype' in data_map:
            zout.writestr('mimetype', data_map['mimetype'], compress_type=zipfile.ZIP_STORED)
        for name in namelist:
            if name == 'mimetype': continue
            zout.writestr(name, data_map[name], compress_type=zipfile.ZIP_DEFLATED)
    print(f"Wrote EPUB to {output_epub}")

if __name__ == '__main__':
    main()
