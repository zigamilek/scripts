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

def init_driver():
    options = Options()
    options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_html(driver, url):
    print(f"\nFetching HTML for {url}")
    driver.get(url)
    time.sleep(3)  # Wait for JavaScript to load
    return driver.page_source

def parse_html(html):
    print("Parsing HTML content")
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def extract_mp3_link_from_json(soup):
    print("Extracting MP3 link from JSON data")
    script_tag = soup.find('script', {'type': 'application/ld+json', 'id': '__jw-ld-json'})
    if script_tag:
        print("  Found the <script> tag with JSON data")
        json_data = json.loads(script_tag.string)
        if json_data and isinstance(json_data, list):
            mp3_url = json_data[0].get('contentUrl')
            if mp3_url:
                print(f"  Found MP3 URL: {mp3_url}")
                return mp3_url
            else:
                print("  MP3 URL not found in JSON data")
        else:
            print("  JSON data is empty or not in expected format")
    else:
        print("  The <script> tag with JSON data not found")
    return None

def extract_author(description):
    patterns = [
        r"Napisal: (.+)\.",
        r"Napisala: (.+)\.",
        r"Avtor: (.+)\.",
        r"Avtorica: (.+)\.",
        r"Napisali: (.+)\.",
        r"Avtor besedila: (.+)\.",
        r"Avtorica besedila: (.+)\."
    ]
    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            return match.group(1).strip()
    return "Unknown Author"

def extract_podcast_details(soup):
    print("Extracting podcast details")
    podcast_item = soup.find('div', class_='podcast-item')
    
    title_tag = podcast_item.find('h3')
    if title_tag:
        title = title_tag.text.strip()
    else:
        print("  Title not found")
        title = "Unknown Title"
    
    date_tag = podcast_item.find('p', class_='media-meta')
    if date_tag:
        date_str = date_tag.text.strip()
        date = datetime.strptime(date_str, "%d.%m.%Y").strftime("%Y-%m-%d")
    else:
        print("  Date not found")
        date = "Unknown Date"
    
    description_tag = podcast_item.find('div', class_='col-md-12').find('p')
    if description_tag:
        description = description_tag.text.strip()
        author = extract_author(description)
    else:
        print("  Description not found")
        description = "No description available"
        author = "Unknown Author"
        
    print(f"  Extracted details - Title: {title}, Date: {date}, Description: {description}, Author: {author}")
    return {
        'title': title,
        'description': description,
        'date': date,
        'author': author
    }

def sanitize_filename(filename):
    return "".join(x for x in filename if x.isalnum() or x in "._- ")

def add_id3_tags(file_path, title, author, date, description):
    print(f"Adding ID3 tags to {file_path}")
        
    # Load the file and add an ID3 tag if it doesn't exist
    audio = File(file_path, easy=True)
    if audio is None:
        audio = EasyID3()
    else:
        try:
            audio = EasyID3(file_path)
        except ID3NoHeaderError:
            audio = EasyID3()
        
    audio['title'] = title
    audio['artist'] = author  # Use the extracted author
    audio['album'] = "Lahko noč, otroci"
    audio['albumartist'] = "Lahko noč, otroci"
    audio['genre'] = "Pravljice"
    audio['date'] = date
    audio.save(file_path)

    # Adding a comment with the description
    audio = ID3(file_path)
    audio.add(COMM(encoding=3, lang='eng', desc='desc', text=description))
        
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

def download_mp3(mp3_url, title, author, date, description, output_folder, downloaded_files, episode_link):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    print(f"\nDownloading MP3 from {mp3_url}")
    response = requests.get(mp3_url, headers=headers, stream=True)
    if response.status_code == 200:
        sanitized_title = sanitize_filename(title)
        sanitized_author = sanitize_filename(author)
        file_name = f"{sanitized_title} ({sanitized_author}).mp3"
        file_path = os.path.join(output_folder, file_name)
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"  Downloaded {file_path}")
        with open(downloaded_files, 'a') as file:
            file.write(f"{episode_link}\n")
            
        description = f"URL: {episode_link}\n\n{description}"

        # Add ID3 tags
        add_id3_tags(file_path, title, author, date, description)
            
        return file_path
    else:
        print(f"  Failed to download MP3 from {mp3_url} with status code {response.status_code}")
        return None

def save_episode_details(details, file_path):
    details_file_path = file_path.replace(".mp3", "") + "-details.txt"
    with open(details_file_path, 'w') as file:
        file.write(f"Naslov: {details['title']}\n")
        file.write(f"Datum: {details['date']}\n")
        file.write(f"\n{details['description']}\n")
    print(f"  Saved episode details to {details_file_path}")

def extract_episode_links(soup):
    print("Extracting episode links")
    episode_links = []
    items = soup.find_all('div', class_='podcast-item')
    for item in items:
        link_tag = item.find('a', href=True)
        if link_tag:
            link = link_tag['href']
            if link:
                episode_links.append("https://www.rtvslo.si" + link)
    print(f"  Found {len(episode_links)} episode links")
    return episode_links

def get_all_episode_links(base_url, driver, existing_links):
    print("Getting all episode links")
    all_links = []
    page_number = 0
    while True:
        url = f"{base_url}?page={page_number}"
        html = fetch_html(driver, url)
        soup = parse_html(html)
        episode_links = extract_episode_links(soup)
        if not episode_links:
            break
        for link in episode_links:
            if link in existing_links:
                print(f"  Link already exists in the file: {link}")
                return all_links
            all_links.append(link)
        page_number += 1
    print(f"\nTotal episodes found: {len(all_links)}")
    return all_links

def save_all_episode_links(all_links, output_folder):
    links_file_path = os.path.join(output_folder, "0_all_episode_links.txt")
    with open(links_file_path, 'w') as file:
        for link in all_links:
            file.write(f"{link}\n")
    print(f"\nSaved all episode links to {links_file_path}")

def main(output_folder):
    base_url = 'https://www.rtvslo.si/radio/podkasti/lahko-noc-otroci/54'
    links_file_path = os.path.join(output_folder, "0_all_episode_links.txt")
    downloaded_files_path = os.path.join(output_folder, "0_already_downloaded.txt")

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
        with open(links_file_path, 'w') as file:
            for link in episode_links:
                file.write(f"{link}\n")
            for link in existing_links:
                file.write(f"{link}\n")
    
    # Process links from the file
    with open(links_file_path, 'r') as file:
        all_links = file.read().splitlines()
    
    for episode_link in all_links:
        if episode_link in already_downloaded:
            print(f"  Episode already downloaded: {episode_link}")
            continue
        episode_html = fetch_html(driver, episode_link)
        if episode_html:
            episode_soup = parse_html(episode_html)
                
            details = extract_podcast_details(episode_soup)
            mp3_link = extract_mp3_link_from_json(episode_soup)
                
            if mp3_link:
                file_path = download_mp3(mp3_link, details['title'], details['author'], details['date'], details['description'], output_folder, downloaded_files_path, episode_link)
                if file_path:
                    save_episode_details(details, file_path)
            else:
                print(f"  MP3 link not found for episode: {details['title']}")
        
    driver.quit()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <output_folder>")
    else:
        output_folder = sys.argv[1]
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        main(output_folder)
