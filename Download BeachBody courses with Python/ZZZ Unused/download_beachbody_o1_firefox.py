#!/usr/bin/env python3

import os
import re
import time
import logging
import argparse
import subprocess

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
	TimeoutException,
	NoSuchElementException,
	ElementClickInterceptedException,
	ElementNotInteractableException,
)

# Global set to track downloaded .m3u8 filenames
downloaded_m3u8 = set()

def close_overlay_if_present(driver, logger, wait_time=5):
	"""
	Attempt to close the overlay if the close button is clickable within `wait_time` seconds.
	"""
	try:
		close_btn = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable(
				(By.CSS_SELECTOR, "button[class*='videoPlayerStyled__CloseButton']")
			)
		)
		close_btn.click()
		logger.info("Closed video overlay.")
	except TimeoutException:
		logger.warning("Close button not found or not clickable within timeout.")
	except Exception as e:
		logger.warning(f"Could not close overlay: {e}")


def check_and_accept_waiver(driver, logger, wait_time=10):
	"""
	If there's a waiver dialog with a checkbox + 'accept' button,
	check the box and click accept. If not found, do nothing.
	"""
	try:
		# 1) Wait for the checkbox to appear (class contains "checkboxStyled__Box")
		checkbox = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class*='checkboxStyled__Box']"))
		)
		logger.info("Waiver checkbox found. Clicking to check it...")

		# Option A: Just .click() the checkbox
		checkbox.click()

		# Option B (uncomment if normal click doesn't work):
		# driver.execute_script("arguments[0].setAttribute('checked', 'true');", checkbox)
		# logger.info("Set checkbox to checked='true' via JS")

		# 2) Click the 'accept' button (class contains "videoWaiverStyled__Button")
		accept_button = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='videoWaiverStyled__Button']"))
		)
		logger.info("Clicking the 'Accept' button now.")
		accept_button.click()

		logger.info("Waiver accepted.")
		# Might need a short pause to let the dialog vanish
		# time.sleep(1)

	except TimeoutException:
		logger.info("No waiver dialog found. Skipping waiver check.")
	except ElementClickInterceptedException:
		logger.warning("Could not click the checkbox or accept button—maybe the dialog is behind something.")
	except Exception as e:
		logger.warning(f"Error while checking/accepting waiver: {e}")

##############################################################################
# Helper function: Click Reject All Cookies
##############################################################################
def click_reject_all_cookies(driver, logger, wait_time=10):
	"""
	Detect and click the 'Reject All' button for cookies consent,
	using a partial CSS match for the button.
	"""
	try:
		cookie_reject_button = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='osano-cm-denyAll']"))
		)
		cookie_reject_button.click()
		logger.info("Clicked 'Reject All' for cookies.")
	except TimeoutException:
		logger.warning("Cookie consent dialog not found or already handled.")
	except Exception as e:
		logger.warning(f"Error clicking 'Reject All' button: {e}")


##############################################################################
# Helper to parse program name from page <title>
##############################################################################
def get_program_name(driver):
	"""
	Attempts to parse the program name from the page <title>.
	We'll take the text up to the first '-' or '|' as a guess.
	Fallback to something from the URL if needed.
	"""
	try:
		page_title = driver.title.strip()
		if " - " in page_title:
			return page_title.split(" - ")[0].strip()
		elif " | " in page_title:
			return page_title.split(" | ")[0].strip()
		else:
			return page_title
	except:
		pass

	# Fallback to last part of the URL path if no <title> or parse error
	url_path = driver.current_url.strip("/").split("/")
	return url_path[-2] if len(url_path) >= 2 else url_path[-1]


##############################################################################
# Helper: create valid folder name
##############################################################################
def sanitize_string(name):
	"""
	Remove invalid filesystem characters from the name.
	"""
	return re.sub(r'[\\/*?:"<>|]', '_', name).strip()


##############################################################################
# Helper: Scrape “About [Program Name]” text
##############################################################################
def scrape_about_program_text(driver):
	"""
	Scrapes textual info from the Start Here page:
	  - Program Overview
	  - Description (hero)
	  - Informational sections
	  - About the trainer
	Returns a single string containing all sections.
	"""
	about_text = []

	# 1. Program Overview (partial class match)
	try:
		overview_section = driver.find_element(
			By.CSS_SELECTOR, 'section[class*="ContentOverview__Container"]'
		)
		about_text.append("=== Program Overview ===")
		about_text.append(overview_section.text.strip())
	except NoSuchElementException:
		pass

	# 2. Description (hero) (partial class match)
	try:
		hero_paragraph = driver.find_element(
			By.CSS_SELECTOR, 'p[class*="ContentDetailsHero__Description"]'
		)
		about_text.append("\n=== Description (Hero) ===")
		about_text.append(hero_paragraph.text.strip())
	except NoSuchElementException:
		pass

	# 3. Informational sections (partial class match)
	info_sections = driver.find_elements(
		By.CSS_SELECTOR, 'div[class*="ContentDetailsEditorial__Container"]'
	)
	for idx, section in enumerate(info_sections, start=1):
		about_text.append(f"\n=== Informational Section #{idx} ===")
		about_text.append(section.text.strip())

	# 4. About the Trainer (partial class match for #trainer section)
	try:
		trainer_section = driver.find_element(
			By.CSS_SELECTOR, 'section#trainer[class*="ContentDetails__SectionWrapper"]'
		)
		about_text.append("\n=== About the Trainer ===")
		about_text.append(trainer_section.text.strip())
	except NoSuchElementException:
		pass

	return "\n".join(about_text)


##############################################################################
# Helper: Intercept .m3u8 link via Selenium Wire
##############################################################################
def poll_for_m3u8(driver, timeout=10):
	"""
	Poll the Selenium Wire driver's requests for up to `timeout` seconds,
	looking for a response containing 'Main.m3u8' in the URL.
	Returns the URL if found, else None.
	"""
	start_time = time.time()
	while time.time() - start_time < timeout:
		for request in driver.requests:
			if request.response and "Main.m3u8" in request.url:
				return request.url
		time.sleep(1)
	return None

import time

def click_and_get_new_m3u8(driver, click_element, logger, timeout=15):
	"""
	1) Record the current URLs so we know what's "old".
	2) Clear out driver.requests.
	3) Click some element (card, play button, etc.).
	4) Watch for a brand-new .m3u8 request that wasn't in old_urls.
	5) Return the new URL or None if not found within timeout.
	"""
	logger.info("Preparing to capture new .m3u8 URL after clicking an element...")

	old_urls = {req.url for req in driver.requests if req.response}
	logger.info(f"Captured {len(old_urls)} 'old' URLs before clearing driver.requests.")

	driver.requests.clear()
	logger.info("Cleared driver.requests; performing the click now.")

	try:
		click_element.click()
	except ElementClickInterceptedException:
		logger.warning("Click intercepted by an overlay. Attempting to close the popup.")
		try:
			close_popup_button = WebDriverWait(driver, 5).until(
				EC.element_to_be_clickable((By.CSS_SELECTOR, "div.sidebar-iframe-close"))
			)
			close_popup_button.click()
			logger.info("Closed the overlay popup.")
			# Retry clicking the original element after closing the popup
			click_element.click()
			logger.info("Retried clicking the original element after closing the popup.")
		except (TimeoutException, NoSuchElementException) as e:
			logger.error(f"Failed to close the popup or retry clicking: {e}")
			return None
		except Exception as e:
			logger.error(f"Unexpected error while handling click interception: {e}")
			return None

	logger.info("Clicked on the provided element; polling the network requests for a new .m3u8.")

	# 2) Accept waiver if needed
	check_and_accept_waiver(driver, logger, wait_time=5)   # your function

	start_time = time.time()
	while time.time() - start_time < timeout:
		for r in driver.requests:
			if r.response and "Main.m3u8" in r.url and r.url not in old_urls:
				#logger.info(f"Found a new .m3u8 URL: {r.url}")
				logger.info(f"Found a new .m3u8 URL.")
				return r.url
		time.sleep(0.5)

	logger.warning(f"No new .m3u8 URL found within {timeout} seconds.")
	return None


def process_video_card(driver, card, index, output_folder, logger, section_name, video_number):
	"""
	Processes a single video card:
	1. Extracts video title.
	2. Clicks the video to retrieve the .m3u8 URL.
	3. Downloads the video using yt-dlp with the filename format: [Section Name] [Video Number] - [Video Title].mp4
	4. Closes the video overlay.
		
	Parameters:
	- driver: Selenium WebDriver instance.
	- card: WebElement representing the video card.
	- index: Position of the video within the unlocked videos (not used in filename).
	- output_folder: Directory where the video will be saved.
	- logger: Logger instance for logging.
	- section_name: Name of the section the video belongs to.
	- video_number: Sequential number of the video within its section, including locked videos.
	"""
	global downloaded_m3u8  # Declare the global set
	m3u8_url = None  # Initialize at the start

	try:
		# Extract the video title using XPath
		title_element = card.find_element(By.XPATH, './/p[contains(@class, "ContentVideoSliderItem__Title")]')

		# Attempt various methods to extract the title text
		video_title = title_element.text.strip()

		# If text is empty, try alternative attributes
		if not video_title:
			video_title = title_element.get_attribute('textContent').strip()

		if not video_title:
			video_title = title_element.get_attribute('innerText').strip()

		# Final fallback if title is still empty
		if not video_title:
			logger.warning("Video title text is empty. Using default naming.")
			# Log the HTML of the title_element for debugging
			title_html = title_element.get_attribute('outerHTML')
			logger.debug(f"Title element HTML: {title_html}")
			video_title = f"video_{video_number}"

		sanitized_title = sanitize_string(video_title)
		logger.info(f"Video title extracted: '{video_title}'")

	except NoSuchElementException:
		logger.warning("Video title element not found. Using default naming.")
		sanitized_title = f"video_{video_number}"
		video_title = sanitized_title
	except Exception as e:
		logger.error(f"Unexpected error while extracting video title: {e}")
		sanitized_title = f"video_{video_number}"
		video_title = sanitized_title

	# Scroll into view
	driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
	time.sleep(1)  # Allow potential JavaScript to load title

	# Identify the clickable area inside the card (thumbnail container, etc.)
	try:
		clickable_area = WebDriverWait(card, 10).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[class*="ContentVideoSliderItem__CoverImage"]'))
		)
	except TimeoutException:
		logger.error("Clickable area not found. Skipping this video.")
		return
	except Exception as e:
		logger.error(f"Unexpected error while finding clickable area: {e}")
		return

	# 5) Look for a new .m3u8 request after the video starts playing
	m3u8_url = click_and_get_new_m3u8(driver, clickable_area, logger, timeout=15)

	if m3u8_url:
		# Extract the filename from the URL
		m3u8_filename = os.path.basename(m3u8_url.split('?')[0])  # e.g., "XTB00X3_Main.m3u8"

		if m3u8_filename in downloaded_m3u8:
			logger.info(f"m3u8 '{m3u8_filename}' already downloaded. Skipping download.")
		else:
			# Define the new filename with section name, video number, and video title
			output_file = os.path.join(output_folder, f"{section_name} {video_number:02d} - {sanitized_title}.mp4")
			logger.info(f"Downloading video as '{output_file}'")
			try:
				subprocess.run(["yt-dlp", "-o", output_file, m3u8_url], check=True)
				# Add the filename to the set after successful download
				downloaded_m3u8.add(m3u8_filename)
				logger.info(f"Successfully downloaded '{output_file}'")
			except subprocess.CalledProcessError as e:
				logger.error(f"Failed to download video '{output_file}': {e}")
	else:
		logger.warning(f"No .m3u8 URL found for video '{video_title}'. Skipping download.")

	# 7) Close overlay after the download attempt
	close_overlay_if_present(driver, logger, wait_time=5)
	time.sleep(1)


##############################################################################
# Helper: Download all videos on current tab
##############################################################################
def download_all_videos_on_page(driver, wait, output_folder, logger):
	"""
	Downloads all unlocked videos on the current page, organized by their respective sections.
	Each video filename will include the section name and its sequential number within the section.
	"""
	# Find all section wrappers that contain video sliders
	sections = driver.find_elements(By.CSS_SELECTOR, 'section[class*="ContentDetails__SectionWrapper"]')

	if not sections:
		logger.warning("No video sections found on this page.")
		return

	logger.info(f"Found {len(sections)} sections on this page.")

	for section in sections:
		try:
			# Extract the section name from the <h3> tag
			section_header = section.find_element(By.CSS_SELECTOR, 'h3[class*="ContentVideoSlider__Title"]')
			section_name = section_header.text.strip()
			logger.info(f"Processing section: '{section_name}'")
		except NoSuchElementException:
			# Assign a default section name if not found
			section_name = "Unknown Section"
			logger.warning("Section name not found. Using 'Unknown Section'.")

		# Sanitize the section name for filesystem compatibility
		sanitized_section_name = sanitize_string(section_name)

		# Find all video cards within this section
		video_cards = section.find_elements(By.CSS_SELECTOR, 'section[class*="ContentVideoSliderItem__Container"]')

		if not video_cards:
			logger.warning(f"No video cards found in section '{section_name}'. Skipping this section.")
			continue

		logger.info(f"Found {len(video_cards)} videos in section '{section_name}'.")

		# Iterate through all video cards, assigning a sequential number
		for idx, card in enumerate(video_cards, start=1):
			try:
				# Determine if the video is locked or unlocked
				play_button_img = card.find_element(
					By.CSS_SELECTOR,
					'div[class*="ContentVideoSliderItem__CoverImage"] > img'
				)
				is_locked = "ContentVideoSliderItem__LockedPlayButton" in play_button_img.get_attribute("class")
			except NoSuchElementException:
				# If play button image not found, assume the video is locked
				is_locked = True

			if is_locked:
				logger.info(f"Video #{idx} in section '{section_name}' is locked. Skipping download.")
				continue  # Skip locked videos

			logger.info(f"Processing unlocked video #{idx} in section '{section_name}'")
			process_video_card(driver, card, idx, output_folder, logger, sanitized_section_name, idx)

	logger.info("Done with all unlocked videos on this page!")


def get_xpath(driver, element):
	"""
	Generates an XPath for a given WebElement.
	"""
	script = """
	function getElementXPath(elt) {
		var path = "";
		for (; elt && elt.nodeType == 1; elt = elt.parentNode) {
			var idx = 1;
			for (var sib = elt.previousSibling; sib; sib = sib.previousSibling) {
				if (sib.nodeType == 1 && sib.tagName === elt.tagName) idx++;
			}
			var xname = elt.tagName.toLowerCase();
			if (idx > 1) xname += "[" + idx + "]";
			path = "/" + xname + path;
		}
		return path;
	}
	return getElementXPath(arguments[0]);
	"""
	return driver.execute_script(script, element)


##############################################################################
# Helper: Handle the "Trailer" button if present
##############################################################################
def process_trailer_if_available(driver, program_folder, logger):
	"""
	1) Find the "Trailer" button and click it.
	2) Wait for the overlay to load.
	3) (Optional) Click the player's 'Play' button if needed.
	4) Poll for .m3u8, download it.
	5) Close the overlay after the download finishes.
	"""
	global downloaded_m3u8  # Declare the global set
	try:
		trailer_button = driver.find_element(
			By.XPATH, "//button[span[text()='Trailer']]"
		)
		logger.info("Trailer button found. Clicking...")
		trailer_button.click()

		# --- Wait for overlay/player to appear ---
		time.sleep(1)  # short pause for the overlay to appear

		# --- NEW STEP: Check/Accept Waiver if it appears ---
		check_and_accept_waiver(driver, logger, wait_time=10)

		# (Optional) Some BOD videos need an extra click on the 'Play' button
		try:
			play_btn = WebDriverWait(driver, 5).until(
				EC.element_to_be_clickable((By.CSS_SELECTOR, "button.vjs-play-control"))
			)
			play_btn.click()
			logger.info("Clicked the trailer player 'Play' button.")
		except TimeoutException:
			logger.info("No separate trailer 'Play' button found (maybe auto-plays).")

		# --- Poll for .m3u8 request ---
		m3u8_url = None
		start_time = time.time()
		while time.time() - start_time < 15:
			for req in driver.requests:
				if req.response and "Main.m3u8" in req.url:
					m3u8_url = req.url
					break
			if m3u8_url:
				break
			time.sleep(0.5)

		if m3u8_url:
			# Extract the filename from the URL
			m3u8_filename = os.path.basename(m3u8_url.split('?')[0])  # e.g., "XTB00X3_Main.m3u8"

			if m3u8_filename in downloaded_m3u8:
				logger.info(f"m3u8 '{m3u8_filename}' already downloaded. Skipping download.")
			else:
				output_file = os.path.join(program_folder, "Trailer.mp4")
				#logger.info(f"Downloading trailer from {m3u8_url} -> {output_file}")
				logger.info(f"Downloading trailer as '{output_file}'")
						
				# Blocking call until download finishes
				subprocess.run(["yt-dlp", "-o", output_file, m3u8_url])
				logger.info("Trailer download finished.")

				# Add the filename to the set after successful download
				downloaded_m3u8.add(m3u8_filename)

			# --- Close overlay after download ---
			close_overlay_if_present(driver, logger, wait_time=5)

		else:
			logger.warning("No trailer .m3u8 found. Possibly it's not actually available.")
			# Attempt to close overlay anyway
			close_overlay_if_present(driver, logger, wait_time=2)

	except NoSuchElementException:
		logger.info("No Trailer button found. Skipping trailer.")
	except Exception as e:
		logger.error(f"Error while processing trailer: {e}")
		close_overlay_if_present(driver, logger, wait_time=2)


##############################################################################
# Helper: Process sub-tabs for a program
##############################################################################
def process_program_tabs(driver, wait, program_folder, logger):
	"""
	Finds and processes sub-tabs, skipping "Start Here" and "You May Also Like".
	For each valid tab:
	- Creates a subfolder
	- Navigates to the tab link
	- Downloads videos
	"""
	try:
		# Wait until the tabs wrapper is present
		tabs_wrapper = wait.until(
			EC.presence_of_element_located(
				(By.XPATH, '//div[contains(@class, "ContentTabSwitcher__ContentTabsWrapper")]')
			)
		)
			
		# Find all main tab elements (excluding dropdown items)
		main_tab_elements = tabs_wrapper.find_elements(
			By.XPATH, './/a[contains(@class, "ContentTabSwitcherItem__TabTitle")]'
		)
			
		tab_links = []
		for tab in main_tab_elements:
			# Attempt multiple methods to retrieve text
			tab_text = tab.text.strip()
			if not tab_text:
				tab_text = tab.get_attribute('innerText').strip()
			if not tab_text:
				tab_text = tab.get_attribute('textContent').strip()
			if not tab_text:
				# Use JavaScript as a last resort
				tab_text = driver.execute_script("return arguments[0].innerText;", tab).strip()
			if not tab_text:
				tab_text = driver.execute_script("return arguments[0].textContent;", tab).strip()
				
			href = tab.get_attribute("href")
				
			if not tab_text:
				logger.warning(f"Could not retrieve text for tab with href: {href}")
				continue
				
			# Skip "Start Here" and "You May Also Like"
			if tab_text.lower().startswith("start here") or "you may also like" in tab_text.lower():
				logger.debug(f"Skipping tab '{tab_text}'")
				continue
				
			tab_links.append((tab_text, href))
			
		logger.info(f"Found {len(tab_links)} valid sub-tabs: {[t[0] for t in tab_links]}")
			
		if not tab_links:
			logger.warning("No valid sub-tabs found. Please verify the CSS/XPath selectors and element visibility.")
			
		for tab_text, href in tab_links:
			tab_folder_name = sanitize_string(tab_text)
			tab_folder = os.path.join(program_folder, tab_folder_name)
			os.makedirs(tab_folder, exist_ok=True)
		
			logger.info(f"Visiting tab '{tab_text}' -> {href}")
			driver.get(href)
				
			# Wait for the video cards to load
			try:
				wait.until(
					EC.presence_of_element_located(
						(By.CSS_SELECTOR, 'section[class*="ContentVideoSliderItem__Container"]')
					)
				)
			except TimeoutException:
				logger.warning(f"Timeout waiting for videos to load in tab '{tab_text}'.")
				continue
				
			download_all_videos_on_page(driver, wait, tab_folder, logger)
		
	except TimeoutException:
		logger.warning("Could not find sub-tab navigation. Possibly a unique page layout.")
	except Exception as e:
		logger.error(f"Unexpected error while processing sub-tabs: {e}")


##############################################################################
# Process a single Program URL
##############################################################################
def process_program_url(url, output_folder, completed_file, logger, seleniumwire_options, headless=False):
	logger.info(f"Processing URL: {url}")

	# Create FirefoxOptions
	firefox_options = webdriver.FirefoxOptions()
	firefox_options.add_argument("--disable-gpu")
	if headless:
		firefox_options.add_argument("--headless")  # Enable headless mode
		logger.debug("Headless mode enabled.")

	# Create Firefox driver with Selenium Wire
	driver = webdriver.Firefox(options=firefox_options, seleniumwire_options=seleniumwire_options)
	wait = WebDriverWait(driver, 20)

	# Track whether the process succeeded
	success = False

	try:
		driver.get(url)
		click_reject_all_cookies(driver, logger, wait_time=10)

		program_name = get_program_name(driver)
		program_name = sanitize_string(program_name)
		logger.info(f"Detected program name: {program_name}")

		program_folder = os.path.join(output_folder, program_name)
		os.makedirs(program_folder, exist_ok=True)

		# About text
		about_text = scrape_about_program_text(driver)
		about_file_path = os.path.join(program_folder, f"About {program_name}.txt")
		with open(about_file_path, "w", encoding="utf-8") as f:
			f.write(about_text)
		logger.info(f"Saved About text to {about_file_path}")

		# Trailer
		process_trailer_if_available(driver, program_folder, logger)

		# Videos in Start Here tab
		logger.info("Downloading videos from the 'Start Here' tab...")
		download_all_videos_on_page(driver, wait, program_folder, logger)

		# Sub-tabs
		process_program_tabs(driver, wait, program_folder, logger)

		# If we reached this point without errors, mark success
		success = True

	except Exception as e:
		logger.error(f"Error processing {url}: {e}")

	finally:
		driver.quit()

	# Only mark as completed if success is True
	if success:
		with open(completed_file, "a", encoding="utf-8") as cf:
			cf.write(url + "\n")


##############################################################################
# Main CLI
##############################################################################
def main():
	parser = argparse.ArgumentParser(description="Scrape Beachbody On Demand programs with Firefox.")
	parser.add_argument("--urls-file", required=True, help="Text file containing program URLs.")
	parser.add_argument("--output-folder", required=True, help="Main output folder.")
	parser.add_argument(
		"--log",
		default="INFO",
		choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
		help="Set the logging level (default: INFO)"
	)
	parser.add_argument(
		"--headless",
		action="store_true",
		help="Run Firefox in headless mode."
	)

	args = parser.parse_args()

	# Configure logging
	log_level = getattr(logging, args.log.upper(), logging.INFO)
	logging.basicConfig(
		level=log_level,
		format="%(asctime)s [%(levelname)s] %(message)s",
		handlers=[
			logging.StreamHandler(),
			logging.FileHandler("bod_scraper.log", mode="a", encoding="utf-8")
		]
	)
	seleniumwire_logger = logging.getLogger("seleniumwire")
	seleniumwire_logger.setLevel(logging.WARNING)

	logger = logging.getLogger(__name__)

	# Track completed programs
	completed_file = "completed_programs.txt"
	completed_programs = set()
	if os.path.exists(completed_file):
		with open(completed_file, "r", encoding="utf-8") as f:
			completed_programs = set(line.strip() for line in f if line.strip())

	# Read URLs
	with open(args.urls_file, "r", encoding="utf-8") as f:
		program_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

	os.makedirs(args.output_folder, exist_ok=True)

	seleniumwire_options = {
		# 'verify_ssl': False,   # or other Selenium Wire options if needed
	}

	for url in program_urls:
		#if url in completed_programs:
		#	logger.info(f"URL {url} is already completed. Skipping.")
		#	continue

		process_program_url(
			url=url,
			output_folder=args.output_folder,
			completed_file=completed_file,
			logger=logger,
			seleniumwire_options=seleniumwire_options,
			headless=args.headless  # Pass the headless flag
		)

	logger.info("All done!")


if __name__ == "__main__":
	main()
