#region: Imports
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
#endregion

#region: Helper functions for loading and parsing HTML
def init_driver():
    options = Options()
    options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_html(driver, url):
    logging.info(f"Fetching HTML for {url}")
    driver.get(url)
    time.sleep(3)  # Wait for JavaScript to load
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
def extract_podcast_details(soup):
    logging.debug("Extracting podcast details")
    podcast_item = soup.find('div', class_='podcast-item')
        
    title_tag = podcast_item.find('h3')
    if title_tag:
        title = title_tag.text.strip()
    else:
        logging.warning("Title not found in HTML")
        title = "Unknown Title"
        
    date_tag = podcast_item.find('p', class_='media-meta')
    if date_tag:
        date_str = date_tag.text.strip()
        date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    else:
        logging.warning("Date not found in HTML")
        date = "Unknown Date"
        
    description_tag = podcast_item.find('div', class_='col-md-12').find('p')
    if description_tag:
        description = description_tag.text.strip()
        author = extract_author(description)
        narrator = extract_narrator(description)
        year_of_recording = extract_year_of_recording(description)
    else:
        logging.warning("Description not found in HTML")
        description = "No description available"
        author = "Unknown Author"
        narrator = "Unknown Narrator"
        year_of_recording = "Unknown Year"
            
    logging.info(f"Extracted details: Title='{title}', Date={date}, Author={author}, Narrator={narrator}, Year={year_of_recording}")
    return {
        'title': title,
        'description': description,
        'date': date,
        'author': author,
        'narrator': narrator,
        'year_of_recording': year_of_recording
    }

def extract_mp3_link_from_json(soup):
    logging.debug("Extracting MP3 link from JSON data")
    script_tag = soup.find('script', {'type': 'application/ld+json', 'id': '__jw-ld-json'})
    if script_tag:
        logging.debug("Found the <script> tag with JSON data")
        json_data = json.loads(script_tag.string)
        # Handle both list and object JSON formats
        if isinstance(json_data, list):
            mp3_url = json_data[0].get('contentUrl')
        elif isinstance(json_data, dict):
            mp3_url = json_data.get('contentUrl')
        else:
            logging.warning("JSON data is empty or not in expected format")
            return None
        if mp3_url:
            logging.debug(f"Found MP3 URL: {mp3_url}")
            return mp3_url
        else:
            logging.warning("MP3 URL not found in JSON data")
    else:
        logging.warning("The <script> tag with JSON data not found")
    return None

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

def main(output_folder, dry_run=False):
    base_url = 'https://365.rtvslo.si/oddaja/lahko-noc-otroci/54'
    # Store episode links and downloaded-record in script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    links_file_path = os.path.join(script_dir, "0_all_episode_links.txt")
    downloaded_files_path = os.path.join(script_dir, "0_already_downloaded.txt")

    # Load existing links
    if os.path.exists(links_file_path):
        with open(links_file_path, 'r') as file:
            existing_links = file.read().splitlines()
    else:
        existing_links = []

    # Load already downloaded links
    if os.path.exists(downloaded_files_path):
        with open(downloaded_files_path, 'r') as file:
            already_downloaded = file.read().splitlines()
    else:
        already_downloaded = []

    driver = init_driver()
    
    # Extract new episode links
    episode_links = get_all_episode_links(base_url, driver, existing_links)
    
    # Save the new links to the beginning of the file
    if episode_links:
        if dry_run:
            logging.info(f"Dry run: would write {len(episode_links)} new links to {links_file_path}")
        else:
            with open(links_file_path, 'w') as file:
                for link in episode_links:
                    file.write(f"{link}\n")
                for link in existing_links:
                    file.write(f"{link}\n")
            logging.info(f"Saved all episode links to {links_file_path}")
    
    # Process links from the file
    with open(links_file_path, 'r') as file:
        all_links = file.read().splitlines()
    
    for line_number, episode_link in enumerate(all_links):
        counter = len(all_links) - line_number
        if episode_link in already_downloaded:
            #logging.debug(f"Episode already downloaded: {episode_link}")
            continue
        episode_html = fetch_html(driver, episode_link)
        if episode_html:
            episode_soup = parse_html(episode_html)
                
            details = extract_podcast_details(episode_soup)
            mp3_link = extract_mp3_link_from_json(episode_soup)
                
            if mp3_link:
                if dry_run:
                    logging.info(f"Dry run: would download MP3 from {mp3_link} for episode '{details['title']}'")
                else:
                    file_path = download_mp3(mp3_link, details['date'], details['title'], details['author'], details['narrator'], details['year_of_recording'], details['description'], output_folder, downloaded_files_path, episode_link, counter)
                    if file_path:
                        save_episode_details(details, file_path)
            else:
                logging.warning(f"MP3 link not found for episode: {details['title']}")
        
    driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download 'Lahko noč, otroci' podcast episodes")
    parser.add_argument("-o", "--output-folder", dest="output_folder", required=True, help="Folder to save downloaded MP3 files")
    parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Perform a dry run without downloading or writing files")
    parser.add_argument("-l", "--log-level", dest="log_level", default="INFO", choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"], help="Set logging level")
    args = parser.parse_args()
    # Configure logging according to user-specified level
    logging.basicConfig(level=getattr(logging, args.log_level), format='%(asctime)s %(levelname)s:%(message)s')
    output_folder = args.output_folder
    dry_run = args.dry_run
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    main(output_folder, dry_run)
