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

##############################################################################
# Helper function: Click Reject All Cookies
##############################################################################
def click_reject_all_cookies(driver, wait):
	"""
	Detect and click the 'Reject All' button for cookies consent,
	using a partial CSS match for the button.
	"""
	try:
		cookie_reject_button = wait.until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='osano-cm-denyAll']"))
		)
		cookie_reject_button.click()
		print("Clicked 'Reject All' for cookies.")
	except TimeoutException:
		print("Cookie consent dialog not found or already handled.")
	except Exception as e:
		print(f"Error clicking 'Reject All' button: {e}")


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
def sanitize_folder_name(name):
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


##############################################################################
# Helper: Download all videos on current tab
##############################################################################
def download_all_videos_on_page(driver, wait, output_folder, logger):
	"""
	Finds video cards, scrolls into view, clicks each unlocked video, intercepts .m3u8, 
	downloads via yt-dlp, and skips locked videos.
	"""
	# Refined CSS selector to target <section> tags with class containing "ContentVideoSliderItem__Container"
	video_cards = driver.find_elements(
		By.CSS_SELECTOR,
		'section[class*="ContentVideoSliderItem__Container"]'
	)
		
	total_videos = len(video_cards)
	unlocked_videos = 0
	locked_videos = 0

	logger.info(f"Found {total_videos} video cards on this tab.")
		
	for index, card in enumerate(video_cards, start=1):
		logger.info(f"Processing video card #{index}")

		try:
			# Check if the video is locked by inspecting the play button's classes
			play_button = card.find_element(By.CSS_SELECTOR, 'img[class*="ContentVideoSliderItem__PlayButton"]')
			play_button_classes = play_button.get_attribute("class")
				
			if "ContentVideoSliderItem__LockedPlayButton" in play_button_classes:
				locked_videos += 1
				logger.info(f"Video #{index} is locked. Skipping...")
				continue
			else:
				unlocked_videos += 1
				logger.info(f"Video #{index} is unlocked. Proceeding to download.")
			
		except NoSuchElementException:
			locked_videos += 1
			logger.warning(f"Could not determine if video #{index} is locked. Skipping...")
			continue
		except Exception as e:
			locked_videos += 1
			logger.error(f"Error determining lock status for video #{index}: {e}. Skipping...")
			continue

		try:
			# Scroll the element into view
			driver.execute_script("arguments[0].scrollIntoView({ behavior: 'instant', block: 'center' });", card)
			time.sleep(0.5)

			# Clear previous network requests
			driver.requests.clear()

			# Wait until the card's clickable area is present
			clickable_area = WebDriverWait(card, 10).until(
				EC.element_to_be_clickable(
					(By.CSS_SELECTOR, 'div[class*="ContentVideoSliderItem__CoverImage"]')
				)
			)

			# Log the clickable area's HTML for debugging
			clickable_html = clickable_area.get_attribute('outerHTML')
			logger.debug(f"Clickable area HTML for video card #{index}: {clickable_html}")

			# Click the clickable area using ActionChains
			ActionChains(driver).move_to_element(clickable_area).click().perform()
			logger.info(f"Clicked video card #{index}")
				
		except TimeoutException:
			logger.error(f"Timeout while waiting for video card #{index} to be clickable.")
			continue
		except ElementNotInteractableException:
			logger.error(f"Video card #{index} is not interactable.")
			continue
		except NoSuchElementException:
			logger.error(f"Clickable area not found for video card #{index}.")
			continue
		except Exception as e:
			logger.error(f"Error clicking video card #{index}: {e}")
			continue

		# Poll for up to 10 seconds to get the m3u8 URL
		m3u8_url = poll_for_m3u8(driver, timeout=10)
		if m3u8_url:
			output_file = os.path.join(output_folder, f"video_{index}.mp4")
			logger.info(f"Downloading {m3u8_url} -> {output_file}")

			# Execute yt-dlp command and wait for it to complete
			result = subprocess.run([
				"yt-dlp",
				"-o", output_file,
				m3u8_url
			], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

			if result.returncode == 0:
				logger.info(f"Successfully downloaded video #{index} to {output_file}")
			else:
				logger.error(f"yt-dlp failed for video #{index}. Error: {result.stderr}")

		else:
			logger.warning(f"No Main.m3u8 request found for video card #{index} within 10s.")

		# Attempt to close the video overlay/modal if it's open
		try:
			# Option 1: Press the ESCAPE key
			ActionChains(driver).send_keys(Keys.ESCAPE).perform()
			logger.debug(f"Pressed ESCAPE to close video overlay for video #{index}.")
			time.sleep(1)  # Wait for overlay to close

			# Option 2: If pressing ESCAPE doesn't work, try clicking a close button
			# Uncomment and modify the following lines based on the actual close button's selector
			# close_button = driver.find_element(By.CSS_SELECTOR, 'button[class*="CloseButton"]')
			# close_button.click()
			# logger.debug(f"Clicked close button to close video overlay for video #{index}.")
			# time.sleep(1)

		except Exception as e:
			logger.warning(f"Could not close video overlay for video #{index}: {e}")

		# Optional: wait a bit before proceeding to the next video
		time.sleep(1)

	logger.info(f"Finished processing tab. Total videos: {total_videos}, Unlocked: {unlocked_videos}, Locked: {locked_videos}.")

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
	Looks for a "Trailer" button (by text). If found:
	- Clicks it
	- Waits up to 10 seconds for the m3u8 link
	- Downloads via yt-dlp
	"""
	try:
		trailer_button = driver.find_element(
			By.XPATH, "//button[span[text()='Trailer']]"
		)
		trailer_button.click()
		logger.info("Clicked Trailer button.")

		# Poll for up to 10 seconds to get the m3u8 URL
		m3u8_url = poll_for_m3u8(driver, timeout=10)
		if m3u8_url:
			output_file = os.path.join(program_folder, "Trailer.mp4")
			logger.info(f"Downloading Trailer: {m3u8_url}")
			subprocess.run(["yt-dlp", "-o", output_file, m3u8_url])
		else:
			logger.warning("No Main.m3u8 found after clicking Trailer (waited 10s).")

	except NoSuchElementException:
		logger.info("No Trailer button found.")


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
			tab_folder_name = sanitize_folder_name(tab_text)
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
def process_program_url(url, output_folder, completed_file, logger, seleniumwire_options):
	logger.info(f"Processing URL: {url}")

	# Create FirefoxOptions
	firefox_options = webdriver.FirefoxOptions()
	firefox_options.add_argument("--disable-gpu")

	# Create Firefox driver with Selenium Wire
	driver = webdriver.Firefox(options=firefox_options, seleniumwire_options=seleniumwire_options)
	wait = WebDriverWait(driver, 20)

	# Track whether the process succeeded
	success = False

	try:
		driver.get(url)
		click_reject_all_cookies(driver, wait)

		program_name = get_program_name(driver)
		program_name = sanitize_folder_name(program_name)
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
			seleniumwire_options=seleniumwire_options
		)

	logger.info("All done!")


if __name__ == "__main__":
	main()
