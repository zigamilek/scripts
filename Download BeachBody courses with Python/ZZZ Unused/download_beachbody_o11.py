#!/usr/bin/env python3

import os
import re
import json
import time
import requests
import logging
import argparse
import subprocess
from dotenv import load_dotenv

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
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

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

BOD_EMAIL = os.getenv("BOD_EMAIL")
BOD_PASSWORD = os.getenv("BOD_PASSWORD")

if not BOD_EMAIL or not BOD_PASSWORD:
	raise RuntimeError("Missing BOD_EMAIL or BOD_PASSWORD environment variable.")

# Global set to track downloaded .m3u8 filenames
downloaded_m3u8 = set()

def bod_login(driver, logger, wait_time=10):
	"""
	Navigates to beachbodyondemand.com homepage, rejects cookies if prompted,
	opens the Log In link, waits for the sign in form, fills in email & password,
	and completes the sign in process.
	"""
	# Go to the homepage
	driver.get("https://www.beachbodyondemand.com/?locale=en_US")
	time.sleep(2)  # let page load briefly

	# Attempt to reject cookies
	try:
		cookie_reject_button = WebDriverWait(driver, 5).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='osano-cm-denyAll']"))
		)
		cookie_reject_button.click()
		logger.info("Clicked 'Reject All' cookies (during login).")
	except TimeoutException:
		logger.debug("No cookie dialog found (during login) or already handled.")
	except Exception as e:
		logger.warning(f"Could not reject cookies during login: {e}")

	# Click the "Log In" link
	try:
		login_link = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.LINK_TEXT, "Log In"))
		)
		login_link.click()
		logger.info("Clicked the 'Log In' link.")
	except Exception as e:
		logger.error(f"Failed to find/click the 'Log In' link: {e}")
		return  # Fail early if we can't log in

	# Fill out the email
	try:
		email_input = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.ID, "capture_signIn_signInEmailAddress"))
		)
		email_input.send_keys(BOD_EMAIL)
		logger.info("Entered email address.")
	except Exception as e:
		logger.error(f"Failed to find/fill the email input field: {e}")
		return

	# Fill out the password
	try:
		password_input = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.ID, "capture_signIn_currentPassword"))
		)
		password_input.send_keys(BOD_PASSWORD)
		logger.info("Entered password.")
	except Exception as e:
		logger.error(f"Failed to find/fill the password input field: {e}")
		return

	# Click the "Sign In" button
	try:
		sign_in_button = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sign-in-button"))
		)
		sign_in_button.click()
		logger.info("Clicked 'Sign In'.")
	except Exception as e:
		logger.error(f"Failed to find/click the sign-in button: {e}")

	# Wait for the user's avatar button to ensure we are logged in
	try:
		avatar_button = WebDriverWait(driver, 30).until(
			EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='userAvatarStyled__AvatarButton']"))
		)
		logger.info("User avatar appeared; login successful.")
	except TimeoutException:
		logger.warning("User avatar did not appear within the timeout; login may not have succeeded.")
	except NoSuchElementException:
		logger.warning("User avatar element not found; login may not have succeeded.")
	except Exception as e:
		logger.error(f"Unexpected error while waiting for avatar: {e}")

def close_promo_screen_if_present(driver, logger, wait_time=10):
	"""
	Attempt to close the 'promoScreenStyled__PromoScreenContent' popup by
	clicking the close icon that has a class containing 'promoScreenStyled__PositionedCloseIcon'.
	"""
	try:
		# This waits for the close icon to be clickable if the promo screen is present
		close_icon = WebDriverWait(driver, wait_time).until(
			EC.element_to_be_clickable((By.CSS_SELECTOR, "img[class*='promoScreenStyled__PositionedCloseIcon']"))
		)
		close_icon.click()
		logger.info("Closed the promo popup screen.")
	except TimeoutException:
		logger.debug("Promo popup screen close icon not found within wait_time; may not be present.")
	except Exception as e:
		logger.warning(f"Unexpected error when trying to close promo popup screen: {e}")

def extract_video_details(driver, logger):
	"""
	Extracts video details from the details popup.

	Returns:
		str: Video details.
	"""
	try:
		# Wait until the details modal is visible
		wait = WebDriverWait(driver, 10)
		wait.until(
			EC.visibility_of_element_located(
				(By.CSS_SELECTOR, "div[class*='ContentVideoDetailsModal__CloseButton']")
			)
		)

		# Locate the video details container
		try:
			details_container = driver.find_element(
				By.CSS_SELECTOR, "div[class*='ContentVideoDetailsModal__DetailsContainer']"
			)
			details = details_container.text.strip()
		except NoSuchElementException:
			logger.error("Main details container not found.")
			return ""

		return details

	except Exception as e:
		logger.error(f"Failed to extract video details: {e}")
		return ""

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
def get_program_name(driver, logger):
	"""
	Extracts the program title and trainer's name from the JSON within the <script id="__NEXT_DATA__"> tag.

	Returns:
		str: Formatted folder name as "FirstName LastName - Title".

	Raises:
		Exception: If extraction fails due to missing elements or malformed JSON.
	"""
	try:
		# Locate the <script id="__NEXT_DATA__" type="application/json"> tag
		script_element = driver.find_element(By.ID, "__NEXT_DATA__")
		script_json = script_element.get_attribute('innerHTML')

		# Parse the JSON content
		data = json.loads(script_json)

		# Navigate through the JSON structure to extract title and trainer's name
		program_data = data['props']['pageProps']['reactQueryServerState']['queries'][0]['state']['data']
		title = program_data.get('title', 'Unknown Title')

		trainers = program_data.get('trainers', [])
		if trainers:
			first_trainer = trainers[0]
			first_name = first_trainer.get('firstName', 'FirstName')
			last_name = first_trainer.get('lastName', 'LastName')
		else:
			logger.error("No trainers found in the program data.")
			raise Exception("Trainers information is missing.")

		# Format the folder name
		folder_name = f"{first_name} {last_name} - {title}"
		sanitized_folder_name = sanitize_string(folder_name)

		logger.info(f"Program Folder Name: '{sanitized_folder_name}'")
		return sanitized_folder_name

	except NoSuchElementException:
		logger.error("The <script id=\"__NEXT_DATA__\"> tag was not found on the page.")
		raise
	except json.JSONDecodeError:
		logger.error("Failed to parse JSON from the <script id=\"__NEXT_DATA__\"> tag.")
		raise
	except KeyError as e:
		logger.error(f"Missing expected key in JSON data: {e}")
		raise
	except Exception as e:
		logger.error(f"An unexpected error occurred while extracting program name: {e}")
		raise


##############################################################################
# Helper: create valid folder name
##############################################################################
def sanitize_string(name):
	"""
	Remove invalid filesystem characters from the name.
	"""
	# Remove exclamation marks completely
	name = re.sub(r'!', '', name)

	# Replace other invalid filesystem characters with underscores
	name = re.sub(r'[\\/*?:"<>|.]', '_', name)

	return name.strip()


##############################################################################
# Helper: Scrape “About [Program Name]” text
##############################################################################
def scrape_about_program_text(driver, logger):
	"""
	Scrapes textual info from the Start Here page:
	- Program Overview
	- Description (hero)
	- Informational sections
	- About the trainer
	Returns a single string containing all sections.
	"""
	about_text = []
	logger.info("Starting to scrape program text.")
		
	# 1. Program Overview
	try:
		# Locate the Program Overview section by its header text
		program_overview_header = driver.find_element(
			By.XPATH, "//h4[contains(text(), 'Program Overview')]"
		)
		# Assume the parent div contains the statistics and additional info
		overview_section = program_overview_header.find_element(
			By.XPATH, "./ancestor::div[contains(@class, 'ContentOverview__RightSection')]"
		)
        
		about_text.append("=== Program Overview ===")
		logger.info("Found Program Overview section.")
        
		# Extract all statistic elements
		statistics_container = overview_section.find_element(
			By.XPATH, ".//div[contains(@class, 'ContentStatistics__StatisticsContainer')]"
		)
		statistics_elements = statistics_container.find_elements(
			By.XPATH, "./div[contains(@class, 'ContentStatistics__Statistic')]"
		)
		logger.info(f"Found {len(statistics_elements)} statistics elements.")
        
		statistics_text = []
		for stat in statistics_elements:
			try:
				# Try to extract the value
				value_element = stat.find_element(
					By.XPATH, ".//div[contains(@class, 'ContentStatistics__StatisticValue')]"
				)
				value = value_element.text.strip()
				label_element = stat.find_element(
					By.XPATH, ".//p[contains(@class, 'ContentStatistics__StatisticLabel')]"
				)
				label = label_element.text.strip()
				if value and label:
					line = f"{value} {label}"
				else:
					line = label
				logger.info(f"Extracted statistic: {line}")
			except NoSuchElementException:
				# If value is missing, attempt to extract label only
				try:
					label_element = stat.find_element(
						By.XPATH, ".//p[contains(@class, 'ContentStatistics__StatisticLabel')]"
					)
					label = label_element.text.strip()
					line = label
					logger.info(f"Extracted statistic with missing value: {line}")
				except NoSuchElementException:
					logger.warning("Failed to extract statistic label.")
					continue
			statistics_text.append(line)
        
		# Combine statistics with double line breaks
		#overview_text = "\n\n".join(statistics_text)
		overview_text = "\n".join(statistics_text)
		about_text.append(overview_text)
		logger.info("Successfully scraped Program Overview statistics.")
        
		# 2. Additional Overview Sections (Subheader & Description)
		try:
			# Locate all subheaders within the Program Overview section
			subheaders = overview_section.find_elements(
				By.XPATH, ".//p[contains(@class, 'ContentOverviewSections__Subheader')]"
			)
			logger.info(f"Found {len(subheaders)} subheaders in Program Overview.")
            
			for subheader in subheaders:
				subheader_text = subheader.text.strip()
				if subheader_text:
					#about_text.append(f"\n{subheader_text}")
					about_text.append(f"{subheader_text}")
					logger.info(f"Processing Subheader: '{subheader_text}'")
                    
					try:
						# The corresponding description is the next sibling
						description = subheader.find_element(
							By.XPATH, "following-sibling::p[contains(@class, 'ContentOverviewSections__Description')]"
						)
						description_text = description.text.strip()
						about_text.append(description_text)
						logger.info(f"Extracted Description for '{subheader_text}': '{description_text}'")
					except NoSuchElementException:
						logger.warning(f"No Description found for Subheader '{subheader_text}'.")
					except Exception as e:
						logger.error(f"Error extracting Description for '{subheader_text}': {e}")
		except NoSuchElementException:
			logger.warning("No Additional Overview Subheaders found.")
		except Exception as e:
			logger.error(f"Unexpected error while scraping Additional Overview Sections: {e}")
        
		# 3. Footer Text
		try:
			footer_text_element = overview_section.find_element(
				By.XPATH, ".//p[contains(@class, 'ContentOverview__FooterText')]"
			)
			footer_text = footer_text_element.text.strip()
			if footer_text:
				#about_text.append(f"\n{footer_text}")
				about_text.append(f"{footer_text}")
				logger.info("Successfully scraped Footer Text.")
			else:
				logger.info("Footer Text element found but is empty.")
		except NoSuchElementException:
			logger.warning("Footer Text section not found.")
		except Exception as e:
			logger.error(f"Unexpected error while scraping Footer Text: {e}")
    
	except NoSuchElementException:
		logger.warning("Program Overview section not found.")
	except Exception as e:
		logger.error(f"Unexpected error while scraping Program Overview: {e}")
		
	# 4. Description (hero)
	try:
		description_element = driver.find_element(
			By.XPATH, "//p[contains(@class, 'ContentDetailsHero__Description')]"
		)
		description_text = description_element.text.strip()
		about_text.append("\n=== Description ===")
		about_text.append(description_text)
		logger.info("Successfully scraped Description section.")
	except NoSuchElementException:
		logger.warning("Description section not found.")
	except Exception as e:
		logger.error(f"Unexpected error while scraping Description: {e}")
		
	# 5. Informational sections
	try:
		info_sections = driver.find_elements(
			By.XPATH, "//div[contains(@class, 'ContentDetailsEditorial__Container')]"
		)
		logger.debug(f"Found {len(info_sections)} informational sections.")
		for idx, section in enumerate(info_sections, start=1):
			section_text = section.text.strip()
			if section_text:
				about_text.append(f"\n=== Informational Section #{idx} ===")
				about_text.append(section_text)
				logger.debug(f"Scraped Informational Section #{idx}.")
			else:
				logger.debug(f"Informational Section #{idx} is empty.")
	except Exception as e:
		logger.error(f"Unexpected error while scraping Informational Sections: {e}")
		
	# 6. About the Trainer
	try:
		trainer_section = driver.find_element(
			By.XPATH, "//section[@id='trainer' and contains(@class, 'ContentDetails__SectionWrapper')]"
		)
		trainer_text = trainer_section.text.strip()
		about_text.append("\n=== About the Trainer ===")
		about_text.append(trainer_text)
		logger.info("Successfully scraped About the Trainer section.")
	except NoSuchElementException:
		logger.warning("About the Trainer section not found.")
	except Exception as e:
		logger.error(f"Unexpected error while scraping About the Trainer: {e}")
		
	logger.info("Finished scraping program text.")
	return "\n\n".join(about_text)


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
				subprocess.run(
					[
						"yt-dlp",
						"--external-downloader", "aria2c",
						#"--external-downloader-args", "\"-x 16 -k 1M\"",
						"-o", output_file,
						m3u8_url
					],
					check=True
				)
				# Add the filename to the set after successful download
				downloaded_m3u8.add(m3u8_filename)
				logger.info(f"Successfully downloaded '{output_file}'")
			except subprocess.CalledProcessError as e:
				logger.error(f"Failed to download video '{output_file}': {e}")
				output_file = None  # Reset if download failed

		# If the video was downloaded successfully, proceed to extract details
		if output_file and os.path.exists(output_file):
			# 1. Close the video overlay if it's still open
			close_overlay_if_present(driver, logger, wait_time=5)

			# 2) Close any promo popup if it shows up
			close_promo_screen_if_present(driver, logger, wait_time=5)

			try:
				# Click on the details button to open the popup
				details_button = card.find_element(By.CSS_SELECTOR, "[class*='ContentVideoSliderItem__Details']")
				details_button.click()
				logger.info("Clicked on the video details button.")

				# Extract video details
				details_content = extract_video_details(driver, logger)

				if details_content:
					# Write details to a .txt file with the same name as the video
					txt_filename = os.path.splitext(output_file)[0] + ".txt"
					with open(txt_filename, "w", encoding="utf-8") as txt_file:
						txt_file.write(details_content)
					logger.info(f"Saved video details to '{txt_filename}'")
				else:
					logger.warning("No details extracted for this video.")

			except NoSuchElementException:
				logger.warning("Details button not found. Skipping video details extraction.")
			except Exception as e:
				logger.error(f"Error while extracting video details: {e}")
			finally:
				# Close the details popup
				try:
					close_button = driver.find_element(By.CSS_SELECTOR, "[class*='ContentVideoDetailsModal__CloseButton']")
					close_button.click()
					logger.info("Closed the video details popup.")
				except Exception as e:
					logger.error(f"Failed to close video details popup: {e}")

	else:
		logger.warning(f"No .m3u8 URL found for video '{video_title}'. Skipping download.")

	# 7) Close overlay after the download attempt
	close_overlay_if_present(driver, logger, wait_time=5)

	# 2) Close any promo popup if it shows up
	close_promo_screen_if_present(driver, logger, wait_time=5)
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
				subprocess.run(
					[
						"yt-dlp",
						"--external-downloader", "aria2c",
						#"--external-downloader-args", "\"-x 16 -k 1M\"",
						"-o", output_file,
						m3u8_url
					],
					check=True
				)
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

def click_and_get_new_file(driver, clickable_element, logger, timeout=15):
	"""
	Similar to click_and_get_new_m3u8, but polls for a newly requested file
	(e.g. PDF, DOCX, etc.). If it simply opens a new webpage in a *new tab*, we 
	won't get a direct downloadable request from Selenium Wire, but we still 
	want to close that new tab after checking.

	Returns the matching request URL if found (ends with known file extension),
	else None.
	"""
	logger.info("Preparing to capture new file URL after clicking on a resource card...")

	# Keep track of currently open windows/tabs so we can detect if a new one appears
	old_windows = set(driver.window_handles)

	# Collect old (existing) URLs so we know what's "already requested"
	old_urls = {req.url for req in driver.requests if req.response}
	logger.debug(f"Captured {len(old_urls)} 'old' URLs. Clearing driver.requests now.")

	# Clear out driver.requests so new requests are easier to detect
	driver.requests.clear()

	# Known file extensions to look for
	known_file_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx",
							".png", ".jpg", ".jpeg", ".zip", ".txt"]

	new_file_url = None
	try:
		# Attempt to click the resource card element
		try:
			clickable_element.click()
		except ElementClickInterceptedException:
			logger.warning("Click on file resource was intercepted. Trying JS click on the same element.")
			try:
				driver.execute_script("arguments[0].click();", clickable_element)
				logger.info("JS-based click on resource card succeeded.")
			except Exception as e:
				logger.error(f"Failed to force-click the file resource: {e}")
				return None
		except Exception as e:
			logger.error(f"Failed to click the file resource: {e}")
			return None

		start_time = time.time()

		# Poll for new requests that look like a file download
		while time.time() - start_time < timeout:
			for r in driver.requests:
				if r.response and (r.url not in old_urls):
					url_lower = r.url.lower()
					if any(url_lower.endswith(ext) for ext in known_file_extensions):
						new_file_url = r.url
						logger.info(f"Found a new file URL: {new_file_url}")
						break
			if new_file_url:
				break
			time.sleep(0.5)

		if not new_file_url:
			logger.warning(f"No new file download requests found within {timeout} seconds.")

	finally:
		# Regardless of whether we found a file or not, close any newly opened tabs
		new_windows = set(driver.window_handles) - old_windows
		if new_windows:
			logger.info(f"Detected {len(new_windows)} new tab(s). Closing them now.")
			for handle in new_windows:
				driver.switch_to.window(handle)
				driver.close()

			# Switch back to the original window if it still exists:
			remaining_windows = set(driver.window_handles)
			# Intersection with old_windows ensures the original is still there
			still_existing_originals = list(remaining_windows & old_windows)
			if still_existing_originals:
				logger.debug("Switching back to the original tab/window.")
				driver.switch_to.window(still_existing_originals[0])
			else:
				logger.debug("Original window not found among handles (unexpected).")

	return new_file_url

def process_file_card(driver, card, index, output_folder, logger, section_name, file_number):
	"""
	1. Extracts the file 'title' from the resource card.
	2. Attempts to find some clickable area (icon container or fallback to the entire card).
	3. Clicks it (using JS click if necessary) to trigger/inspect the new file request.
	4. If we detect a valid file request from Selenium Wire, we download the file.
	5. If it opens a web page (instead of downloading a file) or we detect no new response,
	we skip the resource.
	"""

	# Try to get a user-friendly title for the resource
	try:
		# For example: .//p[contains(@class, "ResourceCollectionItem__Title")]
		title_elm = card.find_element(By.CSS_SELECTOR, 'p[class*="ResourceCollectionItem__Title"]')
		resource_title = title_elm.text.strip() or "Unnamed Resource"
	except NoSuchElementException:
		logger.warning("Could not find title element within resource card.")
		resource_title = "Unnamed Resource"
	except Exception as e:
		logger.error(f"Unexpected error while extracting resource title: {e}")
		resource_title = "Unnamed Resource"

	sanitized_title = sanitize_string(resource_title)
	logger.info(f"Resource file title: '{resource_title}'")

	# Scroll the card into view so that it's not offscreen
	driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card)
	time.sleep(1)

	########################################################################
	# Attempt to locate a specifically clickable sub-element
	# e.g. the "IconContainer" if present, else fallback to the entire card.
	########################################################################
	clickable_area = None

	try:
		# Try the icon container first (if that’s actually clickable in this layout)
		clickable_area = card.find_element(By.CSS_SELECTOR, 'div[class*="ResourceCollectionItem__IconContainer"]')
		logger.debug("Found clickable IconContainer inside resource card.")
	except NoSuchElementException:
		logger.debug("Could not find IconContainer. Falling back to entire card as clickable area.")
		# fallback to the entire card
		clickable_area = card

	# Now pass this area to our click_and_get_new_file function,
	# which does the actual click + request polling.
	file_url = click_and_get_new_file(driver, clickable_area, logger, timeout=15)
	if not file_url:
		logger.warning(f"No valid file URL found for resource '{resource_title}'. Possibly it opened another page.")
		return

	# Attempt to retrieve the content from Selenium Wire's cached response
	target_request = None
	for r in driver.requests:
		if r.url == file_url and r.response:
			target_request = r
			break

	if not target_request:
		logger.warning(f"Could not locate a valid response for {file_url}. (Unexpected)")
		return

	# Determine a file extension or fallback
	extension = ""
	disposition = target_request.response.headers.get('Content-Disposition', '')
	# e.g.:  Content-Disposition: attachment; filename="MyGuide.pdf"
	possible_name_match = re.search(r'filename=\"?([^\";]+)', disposition)
	if possible_name_match:
		filename_in_header = possible_name_match.group(1).strip()
		_, ext = os.path.splitext(filename_in_header)
		extension = ext.lower()

	# If still empty, parse from URL
	if not extension:
		parsed_name = os.path.basename(file_url.split('?')[0])
		_, ext = os.path.splitext(parsed_name)
		extension = ext.lower()

	# If still empty, fallback
	if not extension:
		extension = ".bin"

	# Now assemble a final local filename
	final_filename = os.path.join(
		output_folder,
		#f"{section_name} {file_number:02d} - {sanitized_title}{extension}"
		f"{sanitized_title}{extension}"
	)

	file_data = target_request.response.body
	if not file_data:
		logger.warning(f"No file data found in response for {file_url}. Skipping.")
		return

	# Save to disk
	try:
		with open(final_filename, "wb") as f:
			f.write(file_data)
		logger.info(f"Downloaded resource file -> {final_filename}")
	except Exception as e:
		logger.error(f"Failed to write file '{final_filename}': {e}")


def download_all_files_on_page(driver, wait, output_folder, logger):
	"""
	Finds all 'file' cards (divs with classes containing ResourceCollectionItem__Container),
	attempts to download them if they actually trigger a direct file request.
	Files that open a new webpage (instead of a download request) are ignored.
	"""
	file_cards = driver.find_elements(By.CSS_SELECTOR, 'div[class*="ResourceCollectionItem__Container"]')

	if not file_cards:
		logger.info("No resource file cards found on this page.")
		return

	logger.info(f"Found {len(file_cards)} resource file card(s) on this page.")

	for idx, card in enumerate(file_cards, start=1):
		logger.info(f"Processing resource file card #{idx}.")
		process_file_card(
			driver=driver,
			card=card,
			index=idx,
			output_folder=output_folder,
			logger=logger,
			section_name=os.path.basename(output_folder),  # or pass in the sanitized tab/section name
			file_number=idx
		)

	logger.info("Finished processing all resource file cards on this page!")
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
				
			# Wait for the video cards (or resource cards) to load
			try:
				wait.until(
					EC.presence_of_element_located(
						(By.CSS_SELECTOR, 'section[class*="ContentVideoSliderItem__Container"], '
										'div[class*="ResourceCollectionItem__Container"]')
					)
				)
			except TimeoutException:
				logger.warning(f"Timeout waiting for content to load in tab '{tab_text}'.")

			# Download any videos
			download_all_videos_on_page(driver, wait, tab_folder, logger)

			# Download any resources/files
			download_all_files_on_page(driver, wait, tab_folder, logger)

	except TimeoutException:
		logger.warning("Could not find sub-tab navigation. Possibly a unique page layout or no tabs.")
	except Exception as e:
		logger.error(f"Unexpected error while processing sub-tabs: {e}")


##############################################################################
# Process a single Program URL
##############################################################################
def process_program_url(url, output_folder, completed_file, logger, seleniumwire_options, headless=False, browser="chrome"):
	logger.info(f"Processing URL: {url} with browser: {browser.capitalize()}")

	driver = None  # Initialize driver variable

	if browser.lower() == "chrome":
		# Configure ChromeOptions
		chrome_options = webdriver.ChromeOptions()
		chrome_options.add_argument("--disable-gpu")
		chrome_options.add_argument("--window-size=1920,1080")
		chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
		chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
		if headless:
			chrome_options.add_argument("--headless")  # Enable headless mode
			logger.debug("Headless mode enabled for Chrome.")

		# Optional: Add any additional Chrome options here

		try:
			# Initialize Chrome WebDriver with Selenium Wire
			driver = webdriver.Chrome(
				options=chrome_options,
				seleniumwire_options=seleniumwire_options
			)
			wait = WebDriverWait(driver, 20)

			# Track whether the process succeeded
			success = False

			try:
				# 1) Log in first
				bod_login(driver, logger, wait_time=10)

				# 2) Now navigate to the actual program URL
				driver.get(url)

				click_reject_all_cookies(driver, logger, wait_time=10)

				program_name = get_program_name(driver, logger)
				logger.info(f"Detected program name: {program_name}")

				program_folder = os.path.join(output_folder, program_name)
				os.makedirs(program_folder, exist_ok=True)

				# About text
				about_text = scrape_about_program_text(driver, logger)
				#about_file_path = os.path.join(program_folder, f"About {program_name}.txt")
				about_file_path = os.path.join(program_folder, f"About.txt")
				with open(about_file_path, "w", encoding="utf-8") as f:
					f.write(about_text)
				logger.info(f"Saved About text to {about_file_path}")

				# Trailer
				process_trailer_if_available(driver, program_folder, logger)

				# Videos in Start Here tab
				logger.info("Downloading videos from the 'Start Here' tab...")
				download_all_videos_on_page(driver, wait, program_folder, logger)

				# Download any resources/files
				download_all_files_on_page(driver, wait, program_folder, logger)

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

		except Exception as e:
			logger.exception(f"An error occurred while processing URL {url} with Chrome: {e}")
		finally:
			if driver:
				try:
					driver.quit()
				except Exception as e:
					logger.warning(f"Error quitting Chrome driver: {e}")

	elif browser.lower() == "firefox":
		# Configure FirefoxOptions
		firefox_options = webdriver.FirefoxOptions()
		firefox_options.add_argument("--disable-gpu")
		if headless:
			firefox_options.add_argument("--headless")  # Enable headless mode
			logger.debug("Headless mode enabled for Firefox.")

		# Specify the path to the system-installed Firefox if necessary
		# firefox_options.binary_location = "/usr/bin/firefox"

		# Optional: Add any additional Firefox options here

		try:
			# Initialize Firefox WebDriver with Selenium Wire
			driver = webdriver.Firefox(
				options=firefox_options,
				seleniumwire_options=seleniumwire_options
			)
			wait = WebDriverWait(driver, 20)

			# Track whether the process succeeded
			success = False

			try:
				# 1) Log in first
				bod_login(driver, logger, wait_time=10)

				# 2) Now navigate to the actual program URL
				driver.get(url)

				click_reject_all_cookies(driver, logger, wait_time=10)

				program_name = get_program_name(driver, logger)
				logger.info(f"Detected program name: {program_name}")

				program_folder = os.path.join(output_folder, program_name)
				os.makedirs(program_folder, exist_ok=True)

				# About text
				about_text = scrape_about_program_text(driver, logger)
				#about_file_path = os.path.join(program_folder, f"About {program_name}.txt")
				about_file_path = os.path.join(program_folder, f"About.txt")
				with open(about_file_path, "w", encoding="utf-8") as f:
					f.write(about_text)
				logger.info(f"Saved About text to {about_file_path}")

				# Trailer
				process_trailer_if_available(driver, program_folder, logger)

				# Videos in Start Here tab
				logger.info("Downloading videos from the 'Start Here' tab...")
				download_all_videos_on_page(driver, wait, program_folder, logger)

				# Download any resources/files
				download_all_files_on_page(driver, wait, program_folder, logger)

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

		except Exception as e:
			logger.exception(f"An error occurred while processing URL {url} with Firefox: {e}")
		finally:
			if driver:
				try:
					driver.quit()
				except Exception as e:
					logger.warning(f"Error quitting Firefox driver: {e}")

	else:
		logger.error(f"Unsupported browser: {browser}. Supported browsers are 'chrome' and 'firefox'.")


##############################################################################
# Main CLI
##############################################################################
def main():
	parser = argparse.ArgumentParser(description="Scrape Beachbody On Demand programs with Selenium.")
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
		help="Run the browser in headless mode."
	)
	parser.add_argument(
		"--browser",
		choices=["chrome", "firefox"],
		default="chrome",
		help="Choose the browser to use for scraping (default: chrome)."
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
	seleniumwire_logger.setLevel(logging.DEBUG if args.log == "DEBUG" else logging.WARNING)

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
		# 'verify_ssl': False,   # Uncomment if you encounter SSL issues
	}

	for url in program_urls:
		if url in completed_programs:
			logger.info(f"URL {url} is already completed. Skipping.")
			continue

		process_program_url(
			url=url,
			output_folder=args.output_folder,
			completed_file=completed_file,
			logger=logger,
			seleniumwire_options=seleniumwire_options,
			headless=args.headless,   # Pass the headless flag
			browser=args.browser      # Pass the browser selection
		)

	logger.info("All done!")


if __name__ == "__main__":
	main()
