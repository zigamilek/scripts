#region: Imports
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
import time
import sys
import re
from datetime import datetime
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, COMM, ID3NoHeaderError, APIC
import argparse
import logging
import requests  # for scraping podcasti.si
try:
    import requests
except ImportError:
    sys.exit("Error: requests library not found. Please install dependencies with `pip install -r requirements.txt`.")

# Single HTTP session for podcasti.si
session = requests.Session()

# JSON load/save helpers
def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_title(title):
    """Normalize title to a simplified lowercase alphanumeric form for matching."""
    import re
    s = title.lower()
    # Keep letters, numbers, and slovene chars, replace others with space
    s = re.sub(r"[^a-z0-9čšž]+", " ", s)
    return s.strip()
#endregion

#region: Helper functions for loading and parsing HTML
def init_driver():
    options = Options()
    options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_html(driver, url):
    """Fetch the given URL and return its HTML after a brief pause."""
    logging.info(f"Fetching HTML for {url}")
    driver.get(url)
    time.sleep(1)  # brief pause to ensure page load
    return driver.page_source

def parse_html(html):
    logging.debug("Parsing HTML content")
    soup = BeautifulSoup(html, 'html.parser')
    return soup
#endregion

#region: Extract and save all episode links
def get_all_episode_links(base_url, driver, existing_links):
    logging.debug("Getting all episode links")
    all_links = []
    page_number = 1
    while True:
        url = f"{base_url}?p={page_number}"
        logging.debug(f"Fetching page {page_number}: {url}")
        html = fetch_html(driver, url)
        soup = parse_html(html)
        episode_links = extract_episode_links(soup)
        if not episode_links:
            logging.debug(f"No episode links found on page {page_number}, stopping pagination")
            break
        for link in episode_links:
            full_link = link
            logging.debug(f"Processing link: {full_link}")
            if full_link in existing_links:
                logging.debug(f"Link already exists: {full_link}")
                return all_links
            all_links.append(full_link)
        page_number += 1
    logging.debug(f"Total episodes found: {len(all_links)}")
    return all_links

# Replace extract_episode_links to find all anchor tags matching /podkast/lahko-noc-otroci/<id>
def extract_episode_links(soup):
    logging.debug("Extracting episode links")
    episode_links_set = set()
    # Find anchors linking to individual podcast episodes
    for a in soup.find_all('a', href=re.compile(r'^/podkast/lahko-noc-otroci/\d+')):
        rel_link = a.get('href')
        full_link = "https://365.rtvslo.si" + rel_link
        logging.debug(f"Found link pattern: {rel_link} -> {full_link}")
        episode_links_set.add(full_link)
    episode_links = list(episode_links_set)
    logging.debug(f"Found {len(episode_links)} unique episode links in extract_episode_links")
    return episode_links

def save_all_episode_links(all_links, output_folder):
    links_file_path = os.path.join(output_folder, "0_all_episode_links.txt")
    with open(links_file_path, 'w') as file:
        for link in all_links:
            file.write(f"{link}\n")
    logging.info(f"Saved all episode links to {links_file_path}")
#endregion

#region: Extract the details of each podcast episode
# Extract podcast details, with fallback to meta tags if structure has changed
def extract_podcast_details(soup):
    """
    Extract episode details using meta tags on the page.
    """
    logging.debug("Extracting podcast details from meta tags")
    # Title
    title_meta = soup.find('meta', {'name': 'headline'})
    title = title_meta['content'].strip() if title_meta and title_meta.get('content') else 'Unknown Title'
    # Publication date
    # Extract date from subtitle-meta paragraph (e.g., '11.09.2025 6 min')
    date = "Unknown Date"
    p_tag = soup.find('p', class_='subtitle-meta')
    if p_tag:
        text = p_tag.get_text(strip=True)
        m = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
        if m:
            try:
                date = datetime.strptime(m.group(1), '%d.%m.%Y').strftime('%Y-%m-%d')
            except Exception:
                logging.warning(f"Failed to parse date '{m.group(1)}' from subtitle-meta")
    else:
            logging.warning(f"No date found in subtitle-meta text: '{text}'")
    # Full description (includes author, narrator, recording year)
    desc_meta = soup.find('meta', {'name': 'description'})
    description = desc_meta['content'].strip() if desc_meta and desc_meta.get('content') else ''
    # Parse author, narrator, and year from description text
    author = extract_author(description)
    narrator = extract_narrator(description)
    year_of_recording = extract_year_of_recording(description)
    logging.info(f"Extracted details: Title='{title}', Date={date}, Author={author}, Narrator={narrator}, Year={year_of_recording}")
    return {
        'title': title,
        'description': description,
        'date': date,
        'author': author,
        'narrator': narrator,
        'year_of_recording': year_of_recording
    }

def extract_author(description):
    patterns = [
        r"Napisal: (.+)[\.\n]",
        r"Napisala: (.+)[\.\n]",
        r"Avtor: (.+)[\.\n]",
        r"Avtorica: (.+)[\.\n]",
        r"Napisali: (.+)[\.\n]",
        r"Avtorji: (.+)[\.\n]",
        r"Avtorji besedil: (.+)[\.\n]",
        r"Avtorji literarnih del: (.+)[\.\n]",
        r"Avtor besedila: (.+)[\.\n]",
        r"Avtorica besedila: (.+)[\.\n]",
        r"Avtor literarnega dela: (.+)[\.\n]",
        r"Avtorica literarnega dela: (.+)[\.\n]"
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(1).strip().rstrip(".")
        
    # Check for specific strings if no author is found
    if "Slovenska ljudska pripovedka" in description:
        return "Slovenska ljudska pripovedka"
    elif "Slovenska ljudska" in description:
        return "Slovenska ljudska"
    
    # Check for any string ending with " pravljica"
    pravljica_match = re.search(r"(\w+ pravljica)\.", description)
    if pravljica_match:
        return pravljica_match.group(1).strip()
    
    # Check for any string ending with " pripovedka"
    pripovedka_match = re.search(r"(\w+ pripovedka)\.", description)
    if pripovedka_match:
        return pripovedka_match.group(1).strip()
        
    return "Unknown Author"

def extract_narrator(description):
    patterns = [
        r"Pripovedovalec: (.+)[\.\n]",
        r"Pripovedovalka: (.+)[\.\n]",
        r"Pripovedovalci: (.+)[\.\n]",
        r"Pripoveduje: (.+)[\.\n]",
        r"Pripovedujeta: (.+)[\.\n]",
        r"Pripovedujejo: (.+)[\.\n]"
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(1).strip().rstrip(".")
    
    return "Unknown Narrator"

def extract_year_of_recording(description):
    match = re.search(r"Posneto.*?(\d{4})", description)
    if match:
        return match.group(1)
    return "Unknown Year"
#endregion

#region: Download the MP3 file and add ID3 tags
def download_mp3(mp3_url, date, title, author, narrator, year_of_recording, description, output_folder, downloaded_files, episode_link, counter):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    logging.info(f"Downloading MP3 from {mp3_url}")
    response = requests.get(mp3_url, headers=headers, stream=True)
    if response.status_code == 200:
        sanitized_title = sanitize_filename(title)
        sanitized_author = sanitize_filename(author).replace(" in", ";")
        sanitized_narrator = sanitize_filename(narrator).replace(",", ";").replace(" in", ";")
        file_name = f"{counter} - {date} - {sanitized_title} [prip. {sanitized_narrator}, {year_of_recording}] ({sanitized_author}).mp3"
        file_path = os.path.join(output_folder, file_name)
            
        # Ensure the final path does not exceed 250 characters
        if len(file_path) > 250:
            excess_length = len(file_path) - 250
            # Trim the filename part, keeping the extension intact
            file_name = file_name[:len(file_name) - excess_length - 4] + ".mp3"
            file_path = os.path.join(output_folder, file_name)
            
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        logging.info(f"Downloaded {file_path}")
        with open(downloaded_files, 'a') as file:
            file.write(f"{episode_link}\n")
            
        description = f"URL: {episode_link}\n\n{description}"

        # Add ID3 tags
        add_id3_tags(file_path, date, title, author, narrator, year_of_recording, description, counter, episode_link)
            
        return file_path
    else:
        logging.warning(f"Failed to download MP3 ({response.status_code}): {mp3_url}")
        return None

def sanitize_filename(filename):
    replacements = {
        'č': 'c', 'š': 's', 'ž': 'z', 'ć': 'c', 'đ': 'd',
        'Č': 'C', 'Š': 'S', 'Ž': 'Z', 'Ć': 'C', 'Đ': 'D'
    }
    for src, target in replacements.items():
        filename = filename.replace(src, target)
    #return "".join(x for x in filename if x.isalnum() or x in "._- ")
    # Replace any character that is not alphanumeric, dot, underscore, hyphen, space, or comma with an underscore
    return re.sub(r'[^a-zA-Z0-9._\- ,]', '_', filename)

def add_id3_tags(file_path, date, title, author, narrator, year_of_recording, description, track_number, episode_link):
    logging.info(f"Adding ID3 tags to {file_path}")
        
    # Load the file and add an ID3 tag if it doesn't exist
    audio = File(file_path, easy=True)
    if audio is None:
        audio = EasyID3()
    else:
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            audio = EasyID3()
        
    audio['title'] = f"{title} [prip. {narrator}, {year_of_recording}]"
    audio['artist'] = author
    audio['album'] = "Lahko noč, otroci"
    audio['albumartist'] = "Pravljice"
    audio['genre'] = "Pravljice"
    audio['date'] = date
    audio['tracknumber'] = str(track_number)
    audio.save(file_path)

    # Adding a comment with the description
    audio = ID3(file_path)
    audio.add(COMM(encoding=3, lang='eng', desc='description', text=description))
    
    # Adding the episode link as FileURL
    audio.add(COMM(encoding=3, lang='eng', desc='FileURL', text=episode_link))
    
    # Adding the image
    image_url = "https://img.rtvcdn.si/_up/ava/ava_misc/show_logos/54/lo_1400px_md.jpg"
    image_data = requests.get(image_url).content
    audio.add(APIC(
        encoding=3,  # 3 is for utf-8
        mime='image/jpeg',  # image mime type
        type=3,  # 3 is for the cover image
        desc='Cover',
        data=image_data
    ))
    audio.save(file_path)
#endregion

#region: Save episode details in a text file
def save_episode_details(details, file_path):
    # Construct the initial details file path
    details_file_path = file_path.replace(".mp3", "") + f"-details"
        
    # Trim the path to 250 characters if it exceeds the limit
    if len(details_file_path) > 250:
        details_file_path = details_file_path[:250]
        
    # Add the .txt extension
    details_file_path += ".txt"
        
    with open(details_file_path, 'w') as file:
        file.write(f"Naslov: {details['title']}\n")
        file.write(f"Datum: {details['date']}\n")
        file.write(f"\n{details['description']}\n")
    logging.info(f"Saved episode details to {details_file_path}")
#endregion

def format_date_for_podcasti(date_iso):
    """Convert YYYY-MM-DD to 'D. M. YYYY' or 'DD. MM. YYYY' for matching."""
    from datetime import datetime
    try:
        dt = datetime.strptime(date_iso, '%Y-%m-%d')
        # Use single-digit day/month without leading zero
        return dt.strftime(f"{dt.day}. {dt.month}. {dt.year}")
    except Exception:
        return date_iso

import re

def build_podcasti_listing(limit=None):
    """Scrape podcasti.si pagination to collect all episode slugs, titles, dates into podcasti_episodes.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'podcasti_episodes.json')
    base = 'https://podcasti.si/lahko-noc-otroci/'
    # Prepare episodes list and seen slugs
    episodes = load_json(json_path, [])
    existing_slugs = {ep['slug'] for ep in episodes if 'slug' in ep}
    count = 0
    page = 1
    while True:
        page_url = f"{base}?page={page}" if page > 1 else base
        logging.info(f"Fetching podcasti.si listing page: {page_url}")
        resp = session.get(page_url)
        if not resp.ok:
            logging.warning(f"Failed to fetch page {page_url}: {resp.status_code}")
            break
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Find all episode links directly
        link_tags = soup.find_all('a', href=re.compile(r'^/lahko-noc-otroci/ep/'))
        # Debug: print all found link_tags with href and text
        logging.debug(f"[build_podcasti_listing] link_tags found ({len(link_tags)}): {[{'href': a.get('href'), 'text': a.get_text(strip=True)} for a in link_tags]}")
        if not link_tags:
            logging.info("No episode links found on listing page, stopping pagination")
            break
        for a in link_tags:
            # Skip hidden links (e.g., image wrappers)
            cls = a.get('class', [])
            if 'hidden' in cls:
                continue
            rel = a.get('href')
            slug = rel.rstrip('/').split('/')[-1]
            if not slug or slug in existing_slugs:
                continue
            if limit is not None and len(episodes) >= limit:
                logging.info(f"Reached listing limit of {limit} episodes, stopping listing")
                break
            title = a.get_text(strip=True)
            logging.debug(f"[build_podcasti_listing] slug={slug}, title='{title}'")
            episode_link = f"{base}ep/{slug}/"
            episodes.append({
                'slug': slug,
                'title': title,
                'normalized_title': normalize_title(title),
                'episode_link': episode_link,
                'date': None,
                'mp3_url': None,
                'enriched': False
            })
            existing_slugs.add(slug)
        if limit is not None and len(episodes) >= limit:
            logging.info(f"Reached listing limit of {limit} episodes, ending pagination")
            break
        page += 1
    # Persist updated list
    save_json(json_path, episodes)
    logging.info(f"Updated podcasti.si episodes JSON; total {len(episodes)} entries")
    return episodes

def enrich_podcasti_listing(driver, episodes, limit=None):
    """Fetch individual podcasti.si detail pages to enrich each entry with mp3_url."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'podcasti_episodes.json')
    enriched = []
    total = len(episodes)
    count = 0
    for idx, ep in enumerate(episodes, start=1):
        if ep.get('enriched'):
            enriched.append(ep)
            continue
        if limit is not None and count >= limit:
            logging.info(f"Reached podcasti enrich limit of {limit}, skipping remaining episodes")
            enriched.extend(episodes[idx-1:])
            break
        slug = ep.get('slug')
        detail_url = f"https://podcasti.si/lahko-noc-otroci/ep/{slug}/"
        logging.info(f"Enriching podcasti.si entry {idx}/{total}: {detail_url}")
        resp = session.get(detail_url)
        if resp.ok:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Extract date
            date_li = soup.find('i', class_='fas fa-calendar-alt')
            if date_li:
                txt = date_li.find_parent('li').get_text(strip=True)
                m = re.search(r"(\d{2}\.\d{2}\.\d{4})", txt)
                if m:
                    ep['date'] = datetime.strptime(m.group(1), '%d.%m.%Y').strftime('%Y-%m-%d')
            # Extract mp3 URL
            btn = soup.find('button', attrs={'data-audio': True})
            if btn and btn.get('data-audio'):
                ep['mp3_url'] = btn['data-audio']
                ep['enriched'] = True
                count += 1
            else:
                logging.warning(f"MP3 button not found for {detail_url}")
        else:
            logging.warning(f"Failed to fetch {detail_url}: {resp.status_code}")
        enriched.append(ep)
    # Persist updated podcasti episodes JSON
    save_json(json_path, enriched)
    logging.info(f"Enriched podcasti.si JSON with mp3 URLs; total {len(enriched)} entries")
    return enriched

def build_podcasti_mapping(limit=None):
    """Scrape podcasti.si listing pages, fetch each episode detail to map (normalized title, date) to MP3 URL, applying limit."""
    # Load existing podcasti.si episodes to skip already-mapped slugs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    episodes_json_path = os.path.join(script_dir, 'podcasti_episodes.json')
    if os.path.exists(episodes_json_path):
        with open(episodes_json_path, 'r', encoding='utf-8') as ef:
            try:
                episodes_list = json.load(ef)
            except json.JSONDecodeError:
                logging.warning(f"Existing JSON {episodes_json_path} invalid, starting with empty list")
                episodes_list = []
    else:
        episodes_list = []
    # Build mapping of existing keys for skip logic
    existing_keys = {f"{ep['normalized_title']}|{ep['date']}" for ep in episodes_list if 'normalized_title' in ep and 'date' in ep}
    # Determine how many new episodes to fetch based on limit
    if limit is not None:
        new_limit = max(limit - len(episodes_list), 0)
    else:
        new_limit = None
    count = 0
    # If no new entries needed, return existing list
    if new_limit is not None and new_limit <= 0:
        logging.info(f"No new podcasti.si entries needed (existing {len(episodes_list)} >= limit {limit})")
        return episodes_list
    base = "https://podcasti.si/lahko-noc-otroci/"
    page = 1
    stop = False
    while not stop:
        page_url = f"{base}?page={page}" if page > 1 else base
        logging.info(f"Fetching podcasti.si page: {page_url}")
        resp = requests.get(page_url)
        if not resp.ok:
            logging.warning(f"Failed to fetch podcasti.si page {page_url}: {resp.status_code}")
            break
        soup = BeautifulSoup(resp.text, 'html.parser')
        episodes = soup.find_all('div', class_='episode', attrs={'data-podcast': 'lahko-noc-otroci'})
        logging.info(f"Found {len(episodes)} episode entries on page {page}")
        if not episodes:
            break
        # iterate episodes on this page
        for ep in episodes:
            # Stop after reaching new entries limit
            if new_limit is not None and count >= new_limit:
                logging.info(f"Reached new entries limit of {new_limit}, stopping podcasti.si mapping fetch")
                stop = True
                break
            logging.info('')  # blank line before each mapping fetch
            slug = ep.get('data-episode')
            if not slug:
                continue
            detail_url = f"{base}ep/{slug}/"
            logging.info(f"Fetching episode detail: {detail_url}")
            dresp = requests.get(detail_url)
            if not dresp.ok:
                logging.warning(f"Failed to fetch {detail_url}: {dresp.status_code}")
                continue
            dsoup = BeautifulSoup(dresp.text, 'html.parser')
            # Title
            title_tag = dsoup.find('h1', class_='page__title')
            title = title_tag.get_text(strip=True) if title_tag else slug.replace('-', ' ')
            # Date
            date_li = dsoup.find('i', class_='fas fa-calendar-alt')
            if not date_li:
                logging.warning(f"No date element on {detail_url}")
                continue
            date_text = date_li.find_parent('li').get_text(strip=True)
            m = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_text)
            if m:
                # Convert to ISO format
                date_iso = datetime.strptime(m.group(1), "%d.%m.%Y").strftime("%Y-%m-%d")
            else:
                logging.warning(f"Could not parse date for {detail_url}")
                date_iso = ""
            # Compute mapping key
            norm_title = normalize_title(title)
            key = f"{norm_title}|{date_iso}"
            # Skip existing episodes
            if key in existing_keys:
                logging.info(f"Skipping existing entry for {key}")
                continue
            # MP3 URL in button
            btn = dsoup.find('button', attrs={'data-audio': True})
            if not btn:
                logging.warning(f"No audio button on {detail_url}")
                continue
            mp3_url = btn['data-audio']
            # Add new detailed entry
            episodes_list.append({
                'normalized_title': norm_title,
                'date': date_iso,
                'mp3_url': mp3_url,
                'enriched': True
            })
            count += 1
        page += 1
        if stop:
            break
    # Write updated detailed episodes JSON
    with open(episodes_json_path, 'w', encoding='utf-8') as ef:
        json.dump(episodes_list, ef, ensure_ascii=False, indent=2)
    logging.info(f"Updated podcasti.si episodes JSON with total {len(episodes_list)} entries ({count} new)")
    return episodes_list
# --- end podcasti.si linking functions ---

def get_podcasti_url(title, date_iso, mapping):
    """Return the mapped MP3 URL for the given title+date."""
    norm = normalize_title(title)
    # Keys in mapping are strings in the format 'normalized_title|date'
    key = f"{norm}|{date_iso}"
    mp3_url = mapping.get(key)
    logging.info(f"Looking up podcasti.si mapping for exact key: {key} -> {'found' if mp3_url else 'not found'}")
    if not mp3_url:
        # Fallback: match by title only
        matches = [(k, v) for k, v in mapping.items() if k.split('|', 1)[0] == norm]
        if matches:
            fallback_key, fallback_url = matches[0]
            logging.info(f"Fallback: found mapping by title for key={fallback_key}, using that audio URL")
            return fallback_url
        available_keys = list(mapping.keys())[:5]
        logging.info(f"Available mapping keys sample: {available_keys} (showing first 5 of {len(mapping)})")
        logging.debug(f"No mapping entry for key: {key} and no title-only fallback")
        return None
    logging.debug(f"Found podcasti URL for exact key: {key} -> {mp3_url}")
    return mp3_url

def build_rtvslo_listing(driver):
    """Scrape RTVSLO pagination to build or update rtv_episodes.json with episode_link and title."""
    from collections import OrderedDict
    base = 'https://365.rtvslo.si/oddaja/lahko-noc-otroci/54'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'rtvslo_episodes.json')
    # Load existing
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as jf:
            existing = json.load(jf)
        existing_links = {ep['episode_link'] for ep in existing}
        logging.info(f"Loaded {len(existing)} RTVSLO episodes from JSON")
    else:
        existing = []
        existing_links = set()
    episode_map = OrderedDict()
    page = 1
    while True:
        url = f"{base}?p={page}"
        logging.info(f"Fetching RTVSLO listing page: {url}")
        html = fetch_html(driver, url)
        soup = parse_html(html)
        links = soup.find_all('a', href=re.compile(r"^/podkast/lahko-noc-otroci/\d+"))
        if not links:
            break
        for a in links:
            rel = a['href']
            full = f"https://365.rtvslo.si{rel}"
            if full in existing_links:
                logging.info(f"Encountered existing link, stopping at {full}")
                page = None
                break
            title_text = a.get_text(strip=True)
            # skip duration entries like '7 min'
            if re.match(r'^\d+\s*min$', title_text):
                continue
            if full not in episode_map:
                episode_map[full] = title_text
        if page is None:
            break
        page += 1
    # Build list of new episodes with correct titles
    new_eps = [{'episode_link': link, 'title': title, 'enriched': False} for link, title in episode_map.items()]
    combined = new_eps + existing
    with open(json_path, 'w', encoding='utf-8') as jf:
        json.dump(combined, jf, ensure_ascii=False, indent=2)
    logging.info(f"Updated RTVSLO episodes JSON with {len(new_eps)} new entries; total {len(combined)}")
    return combined

def enrich_rtvslo_listing(driver, episodes, downloaded_set, force_enrich, limit=None):
    """Fetch individual RTVSLO episode pages to enrich each entry with details, skipping downloaded by default."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, 'rtvslo_episodes.json')
    enriched = []
    total = len(episodes)
    for idx, ep in enumerate(episodes, start=1):
        link = ep.get('episode_link')
        # blank line before each episode block
        logging.info('')
        # enforce processing limit
        if limit is not None and idx > limit:
            logging.info(f"Reached processing limit of {limit}, skipping enrichment for remaining episodes")
            # append remaining episodes unchanged
            enriched.extend(episodes[idx-1:])
            break
        # Skip episodes already enriched
        if ep.get('enriched', False) and not force_enrich:
            logging.info(f"Skipping already enriched episode {idx} of {total}: {link}")
            enriched.append(ep)
            continue
        ep['already_downloaded'] = link in downloaded_set
        logging.info(f"Working on episode {idx} of {total}: {link} (already_downloaded={ep['already_downloaded']})")
        if ep['already_downloaded'] and not force_enrich:
            logging.info(f"Skipping enrichment for already downloaded: {link}")
            enriched.append(ep)
            continue
        logging.info(f"Enriching RTVSLO episode: {link}")
        html = fetch_html(driver, link)
        soup = parse_html(html)
        details = extract_podcast_details(soup)
        ep.update(details)
        ep['enriched'] = True
        # Check if all details are correct
        unknowns = ['Unknown', 'No description available']
        values = [ep.get('title',''), ep.get('date',''), ep.get('description',''), str(ep.get('year_of_recording',''))]
        ep['all_details_correct'] = not any(any(u in v for u in unknowns) for v in values)
        enriched.append(ep)
    # Write back enriched JSON (including untouched episodes)
    try:
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(enriched, jf, ensure_ascii=False, indent=2)
        logging.info(f"Updated RTVSLO JSON with enrichment; total {len(enriched)} entries (limit={limit})")
    except Exception as e:
        logging.error(f"Failed to write enriched RTVSLO JSON: {e}")
    return enriched

def main(output_folder, dry_run):
    base_url = 'https://365.rtvslo.si/oddaja/lahko-noc-otroci/54'
    # Store episode links and downloaded-record in script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    links_file_path = os.path.join(script_dir, "0_all_episode_links.txt")
    downloaded_files_path = os.path.join(script_dir, "0_already_downloaded.txt")

    # Load existing master metadata from JSON
    json_path = os.path.join(script_dir, 'all_episodes.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as jf:
            master_metadata = json.load(jf)
        existing_links = [ep['episode_link'] for ep in master_metadata]
        logging.info(f"Loaded {len(existing_links)} existing episode links from JSON")
    else:
        master_metadata = []
        existing_links = []

    # Load already downloaded links
    if os.path.exists(downloaded_files_path):
        with open(downloaded_files_path, 'r') as file:
            already_downloaded = file.read().splitlines()
    else:
        already_downloaded = []
    already_downloaded_set = set(already_downloaded)

    driver = init_driver()
    
    # Build and enrich RTVSLO episode list
    rtvslo_eps = build_rtvslo_listing(driver)
    rtvslo_eps = enrich_rtvslo_listing(driver, rtvslo_eps, already_downloaded_set, args.force_enrich_downloaded, args.limit)
    episode_links = [ep['episode_link'] for ep in rtvslo_eps]

    # (links already stored in JSON; skip writing txt files)
    
    # Step 3: Build podcasti.si episodes JSON via pagination
    podcasti_eps = build_podcasti_listing(limit=args.limit)
    # Step 4: Enrich podcasti.si entries with date and mp3_url
    podcasti_eps = enrich_podcasti_listing(driver, podcasti_eps, args.limit)
    # Build lookup mapping from enriched podcasti entries
    mapping = {f"{ep['normalized_title']}|{ep['date']}": ep['mp3_url'] for ep in podcasti_eps if ep.get('enriched')}
    logging.debug(f"[main] podcasti mapping preview: {list(mapping.items())[:5]}")

    # Step 5: Merge mp3_url into RTVSLO episodes and download
    limit = args.limit
    processed = 0
    for ep in rtvslo_eps:
        if not ep.get('enriched', False):
            continue
        # Enforce limit on processed episodes
        if limit is not None and processed >= limit:
            logging.info(f"Reached processing limit of {limit}, skipping remaining episodes")
            break
        # Count this episode attempt
        processed += 1
        if ep.get('already_downloaded', False) and not args.force_enrich_downloaded:
            logging.info(f"[{processed}/{limit}] Skipping already downloaded: {ep['title']}")
            continue
        # Merge mp3_url from podcasti mapping
        key = f"{normalize_title(ep['title'])}|{ep['date']}"
        mp3_val = mapping.get(key)
        logging.debug(f"[main] merging key='{key}' => mp3_url='{mp3_val}'")
        ep['mp3_url'] = mp3_val
        if not ep.get('mp3_url'):
            logging.error(f"[{processed}/{limit}] MP3 link not found for episode: {ep['title']} on {ep.get('date', 'Unknown')}")
            if not dry_run:
                sys.exit(1)
            continue
        logging.info(f"[{processed}/{limit}] Processing: {ep['title']} ({ep['date']}) -> {ep['mp3_url']}")
        if not dry_run:
            file_path = download_mp3(
                ep['mp3_url'], ep['date'], ep['title'],
                ep.get('author',''), ep.get('narrator',''), ep.get('year_of_recording',''),
                ep.get('description',''), output_folder, downloaded_files_path,
                ep['episode_link'], processed
            )
            if file_path:
                save_episode_details(ep, file_path)
                ep['already_downloaded'] = True
        
    # Rewrite rtvslo_episodes.json to reflect updated 'already_downloaded'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rtvslo_json = os.path.join(script_dir, 'rtvslo_episodes.json')
    try:
        with open(rtvslo_json, 'w', encoding='utf-8') as jf:
            json.dump(rtvslo_eps, jf, ensure_ascii=False, indent=2)
        logging.info(f"Final RTVSLO JSON updated with download statuses; total {len(rtvslo_eps)} entries")
    except Exception as e:
        logging.error(f"Failed to update RTVSLO JSON: {e}")
    driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download 'Lahko noč, otroci' podcast episodes")
    parser.add_argument("-o", "--output-folder", dest="output_folder", required=True, help="Folder to save downloaded MP3 files")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Perform a dry run without downloading or writing files")
    parser.add_argument("-l", "--log-level", dest="log_level", default="INFO", choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"], help="Set logging level")
    parser.add_argument('--force-enrich-downloaded', action='store_true',
                        help='Force enrichment of episodes already marked as downloaded')
    parser.add_argument('-n', '--limit', type=int, default=None,
                        help='Maximum number of episodes to process')
    args = parser.parse_args()
    # Configure logging according to user-specified level
    logging.basicConfig(level=getattr(logging, args.log_level), format='%(asctime)s %(levelname)s:%(message)s')
    output_folder = args.output_folder
    dry_run = args.dry_run
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    main(output_folder, dry_run)
