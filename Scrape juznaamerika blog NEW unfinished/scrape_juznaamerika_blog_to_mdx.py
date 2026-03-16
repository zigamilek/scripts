#!/usr/bin/env python3

"""
Scrape juznaamerika.travellerspoint.com blog table of contents and posts.
Save each post as an MDX file with frontmatter and download images.
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

# Add default headers to mimic a browser
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

BASE_URL = 'https://juznaamerika.travellerspoint.com'
TOC_URL = f'{BASE_URL}/toc/'


def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def format_date(date_str):
    # from 'DD.MM.YYYY' to 'YYYY-MM-DD'
    parts = date_str.split('.')
    if len(parts) == 3:
        day, month, year = parts
        return f'{year}-{month}-{day}'
    return date_str


def parse_toc():
    # Table of contents request
    resp = requests.get(TOC_URL, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    posts = []
    for td in soup.find_all('td', attrs={'width': '300px'}):
        a = td.find('a', href=True)
        if not a:
            continue
        href = a['href']
        full_url = urljoin(BASE_URL, href)
        title = a.get_text(strip=True)
        posts.append({'url': full_url, 'title': title})
    # posts are newest first; reverse to oldest-first
    posts.reverse()
    return posts


def scrape_post(post, seq, images_dir):
    print(f'Scraping {post["url"]}')
    # Get post HTML
    resp = requests.get(post['url'], headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    entry = soup.find('div', class_='entry')

    # title
    title_tag = entry.find('h1', class_='entrytitle')
    title = title_tag.get_text(strip=True)

    # date range
    date_tag = entry.find('span', class_='entrydate')
    date_text = date_tag.get_text(strip=True)
    m = re.search(r'(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})', date_text)
    if m:
        date_start_raw, date_end_raw = m.groups()
    else:
        date_start_raw = date_end_raw = date_text
    date_start = format_date(date_start_raw)
    date_end = format_date(date_end_raw)

    # author
    details_p = entry.find('p', class_='entrydetails')
    author_link = details_p.find('a', href=True)
    author = author_link.get_text(strip=True)

    # location
    country_span = details_p.find('span', class_='country_links')
    if country_span:
        location = country_span.find('a').get_text(strip=True)
    else:
        location = ''

    # filename
    slug = slugify(title)
    seq_str = f'{seq:02}'
    filename = f'{seq_str}-{date_start}-{slug}.mdx'

    # ensure images directory
    os.makedirs(images_dir, exist_ok=True)
    content_div = entry.find('div', class_='entrycontent')

    # download and replace images
    for a in content_div.find_all('a', class_='enlarge_image'):
        href = a.get('href', '')
        parsed = urlparse(href)
        qs = parse_qs(parsed.query)
        src = qs.get('src', [None])[0]
        if not src:
            continue
        img_url = src
        img_name = os.path.basename(urlparse(img_url).path)
        img_path = os.path.join(images_dir, img_name)
        if not os.path.exists(img_path):
            r2 = requests.get(img_url, headers=HEADERS)
            r2.raise_for_status()
            with open(img_path, 'wb') as f:
                f.write(r2.content)
        # replace anchor with local img tag using soup.new_tag
        img_tag = soup.new_tag('img', src=f'{images_dir}/{img_name}', alt=img_name)
        a.replace_with(img_tag)

    # parse comments
    comments = []
    for comment_div in soup.find_all('div', class_='comment'):
        det = comment_div.find('p', class_='commentdetails')
        comment_author = det.find('a').get_text(strip=True)
        paras = [p.get_text(strip=True) for p in comment_div.find_all('p') if 'commentdetails' not in p.get('class', [])]
        comment_content = ' '.join(paras)
        comments.append({'author': comment_author, 'content': comment_content})

    # write MDX
    with open(filename, 'w', encoding='utf-8') as mdx:
        mdx.write('---\n')
        mdx.write(f'author: "{author}"\n')
        mdx.write('comments:\n')
        for c in comments:
            mdx.write(f'- author: "{c["author"]}"\n')
            mdx.write(f'  content: "{c["content"]}"\n')
        mdx.write(f"date_end: '{date_end}'\n")
        mdx.write(f"date_start: '{date_start}'\n")
        mdx.write(f'location: "{location}"\n')
        mdx.write(f"post_date: '{date_start}'\n")
        mdx.write(f'title: "{title}"\n')
        mdx.write('---\n\n')
        mdx.write(content_div.decode_contents())
    print(f'Written {filename}')


def main():
    images_dir = 'images'
    posts = parse_toc()
    for idx, post in enumerate(posts, start=1):
        scrape_post(post, idx, images_dir)


if __name__ == '__main__':
    main()
