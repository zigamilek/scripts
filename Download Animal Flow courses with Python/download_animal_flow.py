import os
import re
import time
import logging
from urllib.parse import urlparse
from dotenv import load_dotenv
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import yt_dlp
import argparse
import requests

script_folder = os.path.dirname(os.path.abspath(__file__))

def load_repo_dotenv():
	current_dir = script_folder
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

# Parse command-line arguments for logging level, input file, and output subpath
parser = argparse.ArgumentParser(description="Download Animal Flow Videos")
parser.add_argument(
	'--log',
	default='INFO',
	choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
	help='Set the logging level (default: INFO)'
)
parser.add_argument(
	'--input-file',
	default='class_links_all.txt',
	help='Path to the input file containing URLs (default: class_links_all.txt)'
)
parser.add_argument(
	'--output-subpath',
	default='',
	help='Sub-path to append to the output folder (default: empty string)'
)
args = parser.parse_args()

# Configuration
BASE_OUTPUT_FOLDER = '/Volumes/eulerShare/PaleoPrimal/0 Bodyweight Exercises/Videos/Mike Fitch/Animal Flow/On Demand/0 NEW/'  # Path to the output folder
OUTPUT_SUBPATH = args.output_subpath.strip()  # Sub-path to append
INPUT_FILE = args.input_file  # Input file containing URLs
WAIT_TIME = 10  # Seconds to wait for elements and network requests
LOGIN_SUCCESS_ELEMENT_ID = 'search-icon'  # ID of the element indicating successful login

# Determine the final output folder path
if OUTPUT_SUBPATH:
	OUTPUT_FOLDER = os.path.join(BASE_OUTPUT_FOLDER, OUTPUT_SUBPATH)
else:
	OUTPUT_FOLDER = BASE_OUTPUT_FOLDER

# Ensure output folder exists and is writable
try:
	os.makedirs(OUTPUT_FOLDER, exist_ok=True)
	if not os.access(OUTPUT_FOLDER, os.W_OK):
		print(f"Output folder '{OUTPUT_FOLDER}' is not writable.")
		exit(1)
except Exception as e:
	print(f"Failed to create or access the output folder '{OUTPUT_FOLDER}': {e}")
	exit(1)

# Determine the log file name based on input file name
input_basename = os.path.splitext(os.path.basename(INPUT_FILE))[0]
log_file_name = f"download_animal_flow_{input_basename}.log"

# Set logging level based on argument
log_level = getattr(logging, args.log.upper(), logging.INFO)

# Configure logging
logging.basicConfig(
	level=log_level,
	format='%(asctime)s [%(levelname)s] %(message)s',
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler(log_file_name)
	]
)

# Suppress Selenium Wire's INFO logs
seleniumwire_logger = logging.getLogger('seleniumwire')
seleniumwire_logger.setLevel(logging.WARNING)

def slugify(value):
	"""
	Normalizes string, converts to lowercase, removes non-alpha characters,
	and converts spaces to hyphens.
	"""
	import unicodedata
	value = unicodedata.normalize('NFKD', value).encode(
		'ascii', 'ignore').decode('utf-8')
	value = str(re.sub(r'[^\w\s-]', '', value).strip())  # Remove non-word characters
	value = str(re.sub(r'[-\s]+', '-', value))[0:100]  # Replace spaces and hyphens with single hyphen
	return value

def is_url_accessible(url):
	"""
	Checks if the provided URL is accessible.
	"""
	try:
		response = requests.head(url, allow_redirects=True, timeout=10)
		return response.status_code == 200
	except requests.RequestException:
		return False

def login(driver):
	"""
	Logs into the website using credentials from the .env file.
	"""
	logging.info("Loading environment variables from .env file...")
	load_repo_dotenv()

	email = os.environ.get('EMAIL')
	password = os.environ.get('PASSWORD')

	if not email or not password:
		raise ValueError("Email or Password not found in environment variables!")

	logging.info("Navigating to the login page...")
	driver.get("https://ondemand.animalflow.com/signin/")

	try:
		logging.info("Locating email and password fields...")
		email_field = WebDriverWait(driver, WAIT_TIME).until(
			EC.presence_of_element_located((By.ID, "email"))
		)
		password_field = WebDriverWait(driver, WAIT_TIME).until(
			EC.presence_of_element_located((By.ID, "password"))
		)

		logging.info(f"Entering credentials for email: {email}")
		email_field.send_keys(email)
		password_field.send_keys(password)

		logging.info("Locating and clicking the login button...")
		login_button = WebDriverWait(driver, WAIT_TIME).until(
			EC.element_to_be_clickable((By.XPATH, '//button[@type="submit"]'))
		)
		login_button.click()

		# Wait for the element that indicates a successful login
		WebDriverWait(driver, WAIT_TIME).until(
			EC.presence_of_element_located((By.ID, LOGIN_SUCCESS_ELEMENT_ID))
		)
		logging.info("Login attempt completed successfully!")
	except (NoSuchElementException, TimeoutException) as e:
		logging.error("An element was not found during login or login timed out.")
		raise e

def find_video_url(driver):
	"""
	Extracts the video URL from JWPlayer's playlist.
	"""
	try:
		# Execute JavaScript to get JWPlayer's playlist
		playlist = driver.execute_script("return window.jwplayer().getPlaylist();")
        
		if playlist and len(playlist) > 0:
			media = playlist[0]
			video_url = media.get('file')
			if video_url:
				logging.info(f"Found video URL: {video_url}")
				# Optionally, remove query parameters after '.m3u8'
				if '.m3u8' in video_url:
					video_url = video_url.split('.m3u8')[0] + '.m3u8'
				return video_url
		logging.warning("No video URL found in JWPlayer's playlist.")
	except Exception as e:
		logging.error(f"Error extracting video URL from JWPlayer's playlist: {e}")
	return None

def extract_video_url_from_page(driver):
	"""
	Attempts to extract the video URL directly from the page's JavaScript or embedded data.
	"""
	video_url = None
	try:
		page_source = driver.page_source
		# Example: Search for a specific pattern in the page source
		match = re.search(r'https://cdn\.jwplayer\.com/manifests/[\w\-]+\.m3u8', page_source)
		if match:
			video_url = match.group(0)
			logging.info(f"Extracted video URL from page source: {video_url}")
	except Exception as e:
		logging.error(f"Error extracting video URL from page: {e}")
    
	return video_url

def scrape_page(driver):
	"""
	Scrapes the Title, Metadata, and Description from the current page.
	"""
	data = {}

	try:
		logging.info("Scraping the title...")
		title_element = WebDriverWait(driver, WAIT_TIME).until(
			EC.presence_of_element_located((By.XPATH, '//h1[@role="heading"]'))
		)
		data['title'] = title_element.text.strip()
	except (NoSuchElementException, TimeoutException):
		logging.warning("Title element not found.")
		data['title'] = "No Title"

	try:
		logging.info("Scraping the metadata...")
		metadata_element = WebDriverWait(driver, WAIT_TIME).until(
			EC.presence_of_element_located((By.ID, "meta-data"))
		)
		data['metadata'] = metadata_element.text.strip()
	except (NoSuchElementException, TimeoutException):
		logging.warning("Metadata element not found.")
		data['metadata'] = "No Metadata"

	try:
		logging.info("Scraping the description...")
		description_element = WebDriverWait(driver, WAIT_TIME).until(
			EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "new-video-metadata")]'))
		)
		data['description'] = description_element.text.strip()
	except (NoSuchElementException, TimeoutException):
		logging.warning("Description element not found.")
		data['description'] = "No Description"

	return data

def download_video(output_folder, video_url, filename):
	"""
	Downloads the video using yt-dlp.
	"""
	if not video_url:
		logging.error(f"No video URL provided for {filename}. Skipping download.")
		return

	# Validate the video URL format
	parsed_url = urlparse(video_url)
	if not all([parsed_url.scheme, parsed_url.netloc]):
		logging.error(f"Invalid video URL '{video_url}' for {filename}. Skipping download.")
		return

	# Optional: Check if URL is accessible
	if not is_url_accessible(video_url):
		logging.error(f"Video URL '{video_url}' is not accessible. Skipping download.")
		return

	ydl_opts = {
		'restrictfilenames': True,
		'outtmpl': os.path.join(output_folder, f"{filename}.%(ext)s"),
		'ignoreerrors': True,
		'quiet': True,  # Set to False for more verbosity
		'retries': 3,    # Retry up to 3 times on failures
		'continuedl': True,  # Continue partial downloads
	}

	try:
		logging.info(f"Starting download for {filename} from {video_url}...")
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			ydl.download([video_url])
		logging.info(f"Download completed for {filename}.")
	except yt_dlp.utils.DownloadError as e:
		logging.error(f"yt-dlp failed to download {filename}: {e}")
	except Exception as e:
		logging.error(f"Failed to download video for {filename}: {e}")

def download_video_with_retry(output_folder, video_url, filename, retries=3, delay=5):
	for attempt in range(1, retries + 1):
		try:
			download_video(output_folder, video_url, filename)
			break  # Exit loop if download is successful
		except Exception as e:
			logging.error(f"Attempt {attempt} failed for {filename}: {e}")
			if attempt < retries:
				logging.info(f"Retrying in {delay} seconds...")
				time.sleep(delay)
			else:
				logging.error(f"All {retries} attempts failed for {filename}.")

def save_text(output_folder, filename, title, metadata, description):
	"""
	Saves the scraped text data to a .txt file.
	"""
	text_content = f"Title: {title}\n\nMetadata:\n{metadata}\n\nDescription:\n{description}"
	text_file_path = os.path.join(output_folder, f"{filename}.txt")
	try:
		with open(text_file_path, 'w', encoding='utf-8') as f:
			f.write(text_content)
		logging.info(f"Saved text data for {filename}.")
	except Exception as e:
		logging.error(f"Failed to save text data for {filename}: {e}")

def process_url(driver, url, output_folder):
	"""
	Processes a single URL: navigates, scrapes data, and downloads video.
	"""
	logging.info(f"Processing URL: {url}")
	try:
		driver.get(url)
		WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))  # Wait until the body is loaded

		# Scrape data
		data = scrape_page(driver)
		title = data['title']
		metadata = data['metadata']
		description = data['description']

		# Slugify title for filename
		filename = slugify(title) if title else "untitled"

		# Save text data BEFORE downloading the video
		save_text(output_folder, filename, title, metadata, description)

		# Find video URL from JWPlayer's playlist
		video_url = find_video_url(driver)
		if not video_url:
			logging.warning("Attempting to extract video URL from page source as a fallback.")
			video_url = extract_video_url_from_page(driver)

		# Download video with retries
		download_video_with_retry(output_folder, video_url, filename)

	except Exception as e:
		logging.error(f"An error occurred while processing {url}: {e}")

def main():
	# Configure Selenium Wire options if needed
	selenium_wire_options = {
		'verify_ssl': False,
		'debug': False,  # Set to True for Selenium Wire debug logs
	}

	# Set Firefox options
	firefox_options = Options()
	firefox_options.headless = True  # Run in headless mode

	# Initialize the Selenium Wire WebDriver
	logging.info("Initializing the Firefox browser with Selenium Wire...")
	service = FirefoxService()  # Specify the path to geckodriver if not in PATH
	try:
		driver = webdriver.Firefox(service=service, options=firefox_options, seleniumwire_options=selenium_wire_options)
	except Exception as e:
		logging.error(f"Failed to initialize WebDriver: {e}")
		exit(1)

	try:
		# Log in to the website
		login(driver)

		# Read URLs from the input file
		if not os.path.exists(INPUT_FILE):
			logging.error(f"Input file '{INPUT_FILE}' does not exist.")
			return

		with open(INPUT_FILE, 'r') as f:
			urls = [line.strip() for line in f if line.strip()]

		if not urls:
			logging.error("No URLs found in the input file.")
			return

		logging.info(f"Found {len(urls)} URLs to process.")

		# Process URLs sequentially
		for url in urls:
			process_url(driver, url, OUTPUT_FOLDER)

		logging.info("All URLs have been processed.")
	finally:
		# Clean up and close the browser
		logging.info("Closing the browser...")
		driver.quit()
		logging.info("Browser closed.")

if __name__ == "__main__":
	main()
