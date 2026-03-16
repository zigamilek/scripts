import os
import sys
import argparse
import logging
import time
import json
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
	TimeoutException,
	NoSuchElementException,
	ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import yt_dlp
import subprocess

def click_reject_all_cookies(driver, wait):
	"""
	Detect and click the 'Reject All' button for cookies consent.
	"""
	try:
		# Wait until the cookie consent dialog is present
		cookie_reject_button = wait.until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "button.osano-cm-denyAll"))
		)
		cookie_reject_button.click()
		logging.info("Clicked 'Reject All' for cookies.")
	except TimeoutException:
		logging.info("Cookie consent dialog not found or already handled.")
	except Exception as e:
		logging.error(f"Error clicking 'Reject All' button: {e}")

def configure_logging(log_level, log_file_name):
	"""
	Configures logging for the script.
	"""
	# Set logging level based on argument
	log_level = getattr(logging, log_level.upper(), logging.INFO)

	# Configure logging
	logging.basicConfig(
		level=log_level,
		format='%(asctime)s [%(levelname)s] %(message)s',
		handlers=[
			logging.StreamHandler(),
			logging.FileHandler(log_file_name, encoding='utf-8')
		]
	)

	# Suppress Selenium Wire's INFO logs
	seleniumwire_logger = logging.getLogger('seleniumwire')
	seleniumwire_logger.setLevel(logging.WARNING)

def parse_arguments():
	"""
	Parses command-line arguments.
	"""
	parser = argparse.ArgumentParser(description="Scrape Beachbody On Demand Programs")
	parser.add_argument(
		'input_file',
		help='Path to the file containing program URLs'
	)
	parser.add_argument(
		'output_folder',
		help='Path to the main output folder'
	)
	parser.add_argument(
		'--log',
		default='INFO',
		choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
		help='Set the logging level (default: INFO)'
	)
	args = parser.parse_args()
	return args

def load_finished_programs(file_path):
	"""
	Loads the list of finished programs from a JSON file.
	"""
	if os.path.exists(file_path):
		with open(file_path, 'r', encoding='utf-8') as f:
			try:
				finished = json.load(f)
				logging.debug(f"Loaded {len(finished)} finished programs.")
				return finished
			except json.JSONDecodeError:
				logging.error("Finished programs file is corrupted. Starting fresh.")
				return []
	else:
		return []

def save_finished_programs(file_path, finished_programs):
	"""
	Saves the list of finished programs to a JSON file.
	"""
	with open(file_path, 'w', encoding='utf-8') as f:
		json.dump(finished_programs, f, indent=4)
	logging.debug(f"Saved {len(finished_programs)} finished programs.")

def extract_program_name(url, driver):
	"""
	Extracts the program name from the URL and the page title.
	"""
	try:
		title = driver.title
		logging.debug(f"Page title: {title}")
		# Example title: "Live It Up - High-Energy Workout with Shaun T"
		program_name = title.split(" - ")[0].strip()
		logging.info(f"Extracted program name: {program_name}")
		return program_name
	except Exception as e:
		logging.error(f"Error extracting program name: {e}")
		# Fallback: Extract from URL
		path = urlparse(url).path
		program_segment = path.split('/')[2]  # e.g., 'live-it-up'
		program_name = program_segment.replace('-', ' ').title()
		logging.info(f"Fallback program name: {program_name}")
		return program_name

def create_folders(main_output, program_name):
	"""
	Creates the main program folder and returns its path.
	"""
	program_folder = os.path.join(main_output, program_name)
	os.makedirs(program_folder, exist_ok=True)
	logging.info(f"Created program folder: {program_folder}")
	return program_folder

def extract_about_info(driver):
	"""
	Extracts the 'About [Program Name].txt' information from the 'Start Here' tab.
	"""
	about_info = {}

	try:
		# Program Overview
		overview_section = driver.find_element(By.CSS_SELECTOR, "section.ContentOverview__Container-sc-1qa3yo6-0")
		overview_text = overview_section.text
		about_info['Program Overview'] = overview_text
		logging.debug("Extracted Program Overview.")
	except NoSuchElementException:
		logging.warning("Program Overview section not found.")

	try:
		# Description
		description = driver.find_element(By.CSS_SELECTOR, "p.ContentDetailsHero__Description-as5ixy-10")
		about_info['Description'] = description.text
		logging.debug("Extracted Description.")
	except NoSuchElementException:
		logging.warning("Description section not found.")

	try:
		# Informational Sections
		informational_sections = driver.find_elements(By.CSS_SELECTOR, "div.ContentDetailsEditorial__Container-rs21m-0")
		about_info['Informational Sections'] = []
		for section in informational_sections:
			try:
				title = section.find_element(By.CSS_SELECTOR, "h2.ContentDetailsEditorial__Title-rs21m-4").text
				description = section.find_element(By.CSS_SELECTOR, "div.ContentDetailsEditorial__Description-rs21m-6").text
				about_info['Informational Sections'].append({
					'Title': title,
					'Description': description
				})
			except NoSuchElementException:
				logging.warning("A subsection in Informational Sections is missing title or description.")
		logging.debug("Extracted Informational Sections.")
	except NoSuchElementException:
		logging.warning("Informational Sections not found.")

	try:
		# About the Trainer
		trainer_section = driver.find_element(By.ID, "trainer")
		trainer_name = trainer_section.find_element(By.CSS_SELECTOR, "h3.ContentDetailsTrainer__Headline-sc-1j94zm5-4").text
		trainer_bio = trainer_section.find_element(By.CSS_SELECTOR, "div.ContentDetailsTrainer__TrainerBio-sc-1j94zm5-8").text
		about_info['About the Trainer'] = {
			'Name': trainer_name,
			'Bio': trainer_bio
		}
		logging.debug("Extracted About the Trainer.")
	except NoSuchElementException:
		logging.warning("About the Trainer section not found.")

	return about_info

def save_about_info(program_folder, program_name, about_info):
	"""
	Saves the 'About [Program Name].txt' file with the extracted information.
	"""
	about_file_path = os.path.join(program_folder, f"About {program_name}.txt")
	try:
		with open(about_file_path, 'w', encoding='utf-8') as f:
			f.write(f"Program Overview:\n{about_info.get('Program Overview', 'N/A')}\n\n")
			f.write(f"Description:\n{about_info.get('Description', 'N/A')}\n\n")
            
			informational = about_info.get('Informational Sections', [])
			for idx, section in enumerate(informational, 1):
				f.write(f"Informational Section {idx}:\n")
				f.write(f"Title: {section.get('Title', 'N/A')}\n")
				f.write(f"Description: {section.get('Description', 'N/A')}\n\n")
            
			trainer = about_info.get('About the Trainer', {})
			f.write("About the Trainer:\n")
			f.write(f"Name: {trainer.get('Name', 'N/A')}\n")
			f.write(f"Bio: {trainer.get('Bio', 'N/A')}\n")
		logging.info(f"Saved 'About {program_name}.txt'.")
	except Exception as e:
		logging.error(f"Error saving 'About {program_name}.txt': {e}")

def get_tabs(driver):
	"""
	Retrieves all relevant tabs excluding 'Start Here' and 'You May Also Like'.
	Returns a list of tuples: (tab_name, tab_element)
	"""
	tabs = []
	try:
		nav = driver.find_element(By.CSS_SELECTOR, "nav.ContentTabSwitcher__Nav-sc-3yaexi-1")
		tab_elements = nav.find_elements(By.CSS_SELECTOR, "a.ContentTabSwitcherItem__TabTitle-sc-10y3761-1")
		for tab in tab_elements:
			tab_name = tab.text.strip()
			if "You May Also Like" in tab_name:
				continue  # Skip "You May Also Like"
			if tab_name.lower() == "start here":
				continue  # Skip "Start Here"
			tabs.append((tab_name, tab))
		logging.info(f"Found {len(tabs)} relevant tabs.")
	except NoSuchElementException:
		logging.warning("No tabs found on the page.")
	return tabs

def create_subfolders(program_folder, tabs):
	"""
	Creates subfolders for each tab under the program folder.
	Returns a dictionary mapping tab names to their folder paths.
	"""
	subfolder_paths = {}
	for tab_name, _ in tabs:
		safe_tab_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in tab_name)
		subfolder = os.path.join(program_folder, safe_tab_name)
		os.makedirs(subfolder, exist_ok=True)
		subfolder_paths[tab_name] = subfolder
		logging.info(f"Created subfolder: {subfolder}")
	return subfolder_paths

def download_video(url, output_path):
	"""
	Downloads the video from the given URL using yt-dlp.
	"""
	ydl_opts = {
		'outtmpl': output_path,
		'format': 'best',  # You can specify the format you want
		'quiet': True,
		'no_warnings': True,
		'ignoreerrors': True,
	}

	try:
		with yt_dlp.YoutubeDL(ydl_opts) as ydl:
			ydl.download([url])
		logging.info(f"Downloaded video to {output_path}")
	except Exception as e:
		logging.error(f"yt-dlp failed to download {url}: {e}")

def find_and_download_videos(driver, wait, current_tab, subfolder, program_folder):
	"""
	Finds all video cards in the current tab and downloads them.
	"""
	try:
		# Scroll to the bottom to load all videos
		driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
		time.sleep(2)  # Wait for content to load

		video_cards = driver.find_elements(By.CSS_SELECTOR, "section.ContentVideoSliderItem__Container-pzo2tf-13")
		logging.info(f"Found {len(video_cards)} videos in tab '{current_tab}'.")

		for idx, card in enumerate(video_cards, 1):
			try:
				# Check if it's a "You May Also Like" section
				subtitle_elements = card.find_elements(By.CSS_SELECTOR, "div.ContentVideoSliderItem__Subtitle-pzo2tf-11")
				if any("You May Also Like" in elem.text for elem in subtitle_elements):
					logging.debug("Skipping 'You May Also Like' video.")
					continue

				# Click the video card to load the video
				driver.execute_script("arguments[0].scrollIntoView();", card)
				time.sleep(1)
				card.click()
				logging.debug(f"Clicked on video card {idx} in tab '{current_tab}'.")
				time.sleep(2)  # Wait for video to load

				# Extract m3u8 links from network logs or page
				# Since Selenium doesn't provide network logs by default, we'll try to extract from the page
				# Alternatively, consider using Selenium Wire or a proxy to capture network requests
				# Here, we'll attempt to find the m3u8 link from the page source

				# For simplicity, let's assume the m3u8 URL is present in the page's source after clicking
				page_source = driver.page_source
				m3u8_urls = []
				for line in page_source.splitlines():
					if ".m3u8" in line:
						start = line.find("https://")
						end = line.find(".m3u8") + 5
						if start != -1 and end != -1:
							url = line[start:end]
							m3u8_urls.append(url)
				if not m3u8_urls:
					logging.warning(f"No m3u8 URLs found for video {idx} in tab '{current_tab}'.")
					continue

				# Assume the first m3u8 URL is the highest quality
				m3u8_url = m3u8_urls[0]
				logging.debug(f"Selected m3u8 URL: {m3u8_url}")

				# Define the output video path
				try:
					video_title = card.find_element(By.CSS_SELECTOR, "p.ContentVideoSliderItem__Title-pzo2tf-10").text.strip()
				except NoSuchElementException:
					video_title = f"video_{idx}"
					logging.warning(f"Video title not found. Using default title: {video_title}")
				safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in video_title)
				video_path = os.path.join(subfolder, f"{safe_title}.mp4")

				# Download the video using yt-dlp
				download_video(m3u8_url, video_path)

				# Close the video modal if necessary
				# This depends on the website's behavior; adjust accordingly
				try:
					close_button = driver.find_element(By.CSS_SELECTOR, "button.close")
					close_button.click()
					logging.debug("Closed video modal.")
					time.sleep(1)
				except NoSuchElementException:
					logging.debug("No close button found for video modal.")
			except Exception as e:
				logging.error(f"Error processing video {idx} in tab '{current_tab}': {e}")
	except Exception as e:
		logging.error(f"Error finding videos in tab '{current_tab}': {e}")

def handle_trailer(driver, wait, program_folder, program_name):
	"""
	Handles downloading the trailer video, if available.
	"""
	try:
		trailer_button = driver.find_element(By.XPATH, "//button[contains(., 'Trailer')]")
		driver.execute_script("arguments[0].scrollIntoView();", trailer_button)
		time.sleep(1)
		trailer_button.click()
		logging.info("Clicked on Trailer button.")
		time.sleep(2)  # Wait for trailer to load

		# Extract m3u8 links from the page source
		page_source = driver.page_source
		m3u8_urls = []
		for line in page_source.splitlines():
			if ".m3u8" in line:
				start = line.find("https://")
				end = line.find(".m3u8") + 5
				if start != -1 and end != -1:
					url = line[start:end]
					m3u8_urls.append(url)
		if not m3u8_urls:
			logging.warning("No m3u8 URLs found for Trailer.")
			return

		# Assume the first m3u8 URL is the highest quality
		m3u8_url = m3u8_urls[0]
		logging.debug(f"Selected Trailer m3u8 URL: {m3u8_url}")

		# Define the output video path
		trailer_path = os.path.join(program_folder, f"Trailer.mp4")

		# Download the trailer using yt-dlp
		download_video(m3u8_url, trailer_path)

		# Close the trailer modal if necessary
		try:
			close_button = driver.find_element(By.CSS_SELECTOR, "button.close")
			close_button.click()
			logging.debug("Closed Trailer modal.")
			time.sleep(1)
		except NoSuchElementException:
			logging.debug("No close button found for Trailer modal.")
	except NoSuchElementException:
		logging.info("No Trailer button found for this program.")
	except Exception as e:
		logging.error(f"Error handling Trailer: {e}")

def main():
	# Parse command-line arguments
	args = parse_arguments()

	# Configure logging
	log_file_name = "scraper.log"
	configure_logging(args.log, log_file_name)

	# Load finished programs
	finished_file = "finished_programs.json"
	finished_programs = load_finished_programs(finished_file)

	# Read URLs from input file
	try:
		with open(args.input_file, 'r', encoding='utf-8') as f:
			urls = [line.strip() for line in f if line.strip()]
		logging.info(f"Loaded {len(urls)} URLs from {args.input_file}.")
	except Exception as e:
		logging.error(f"Error reading input file: {e}")
		sys.exit(1)

	# Set up Selenium WebDriver (Chrome)
	options = webdriver.ChromeOptions()
	options.add_argument("--headless")  # Run in headless mode
	options.add_argument("--disable-gpu")
	options.add_argument("--no-sandbox")
	driver = webdriver.Chrome(options=options)
	wait = WebDriverWait(driver, 20)

	try:
		for url in urls:
			if url in finished_programs:
				logging.info(f"Skipping already processed program: {url}")
				continue

			logging.info(f"Processing program: {url}")
			try:
				driver.get(url)
				time.sleep(3)  # Wait for page to load

				# Reject all cookies
				click_reject_all_cookies(driver, wait)

				# Extract program name
				program_name = extract_program_name(url, driver)

				# Create program folder
				program_folder = create_folders(args.output_folder, program_name)

				# Extract 'About' info
				try:
					# Navigate to 'Start Here' tab
					start_here_tab = driver.find_element(By.LINK_TEXT, "Start Here")
					start_here_tab.click()
					logging.debug("Navigated to 'Start Here' tab.")
					time.sleep(2)  # Wait for content to load

					about_info = extract_about_info(driver)
					save_about_info(program_folder, program_name, about_info)
				except NoSuchElementException:
					logging.warning("'Start Here' tab not found.")

				# Get all relevant tabs
				tabs = get_tabs(driver)

				# Create subfolders for tabs
				subfolder_paths = create_subfolders(program_folder, tabs)

				# Iterate through each tab and download videos
				for tab_name, tab_element in tabs:
					try:
						tab_element.click()
						logging.info(f"Navigated to tab: {tab_name}")
						time.sleep(3)  # Wait for tab content to load

						subfolder = subfolder_paths.get(tab_name)
						if not subfolder:
							logging.warning(f"No subfolder found for tab '{tab_name}'. Skipping.")
							continue

						find_and_download_videos(driver, wait, tab_name, subfolder, program_folder)
					except ElementClickInterceptedException:
						logging.error(f"Could not click on tab '{tab_name}'. Skipping.")
					except Exception as e:
						logging.error(f"Error processing tab '{tab_name}': {e}")

				# Handle Trailer
				handle_trailer(driver, wait, program_folder, program_name)

				# Mark as finished
				finished_programs.append(url)
				save_finished_programs(finished_file, finished_programs)
				logging.info(f"Finished processing program: {url}")

			except Exception as e:
				logging.error(f"Error processing program {url}: {e}")

	finally:
		driver.quit()
		logging.info("Selenium WebDriver closed.")

if __name__ == "__main__":
	main()
