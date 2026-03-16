#!/usr/bin/env python3

import os
import sys
import json
import logging
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

################################################################################
# Update these variables to your Les Mills On Demand credentials
EMAIL = "ziga.milek@gmail.com"
PASSWORD = "REMOVED_LES_MILLS_PASSWORD"
################################################################################

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def get_dynamic_html_soup(driver):
	"""
	Grabs the current page source from Selenium
	and returns a BeautifulSoup object.
	"""
	html = driver.page_source
	return BeautifulSoup(html, 'html.parser')

def scrape_all_programs_page(soup, base_url):
	"""
	Parses the “all programs” page. Extracts a structure:
	  {
		 "PROGRAM TITLE": {
		   "description_short": "...",
		   "url": "absolute url"
		 }, ...
	  }
	"""
	logger.info("Parsing all programs from loaded HTML.")
    
	program_cards = soup.find_all('div', attrs={'role': 'listitem'})
	programs_data = {}

	for card in program_cards:
		link = card.find('a', class_='albumCard')
		if not link:
			continue

		title_el = link.find('span', class_='card--title')
		short_desc_el = link.find('span', class_='card--description')
		if not title_el:
			continue

		title = title_el.get_text(strip=True)
		short_desc = short_desc_el.get_text(strip=True) if short_desc_el else ""
        
		relative_url = link.get('href', '')
		if relative_url.startswith("http"):
			full_url = relative_url
		else:
			from urllib.parse import urljoin
			full_url = urljoin(base_url, relative_url)
        
		programs_data[title] = {
			"description_short": short_desc,
			"url": full_url
		}
    
	logger.info(f"Extracted {len(programs_data)} programs from the page.")
	return programs_data

def scrape_program_page(driver, program_url):
	"""
	Visits a given program URL, waits for load,
	then scrapes the long description, workout count, and workout list.

	Returns:
	  {
		"description_long": "...",
		"number_of_workouts": "...",
		"workouts": {
		   "WORKOUT TITLE": {
			  "url": "...",
			  "categories": [...],
			  "duration": "..."
		   }
		}
	  }
	"""
	logger.info(f"Scraping program page: {program_url}")
	driver.get(program_url)

	# Wait a bit for JS content to load
	WebDriverWait(driver, 10).until(
		EC.presence_of_all_elements_located((By.CLASS_NAME, 'desc--row'))
	)

	soup = get_dynamic_html_soup(driver)

	desc_long = ""
	desc_div = soup.find('div', class_='desc--row')
	if desc_div:
		span_el = desc_div.find('span')
		if span_el:
			desc_long = span_el.get_text(strip=True)
    
	# Find workouts count text.
	workouts_count = ""
	p_tags = soup.find_all('p')
	for p in p_tags:
		if p.has_attr('class') and any('styles__WorkoutResultsAmount' in c for c in p['class']):
			workouts_count = p.get_text(strip=True)
			break
    
	# Now gather workout cards
	workouts_dict = {}
	workout_cards = soup.find_all('a', class_='videoCard')
	for w_link in workout_cards:
		title_el = w_link.find('div', class_='title')
		if not title_el:
			continue
        
		workout_title = title_el.get_text(strip=True)

		rel_url = w_link.get('href', '')
		from urllib.parse import urljoin
		workout_url = urljoin(program_url, rel_url)

		duration_div = w_link.find('div', class_='duration')
		duration = duration_div.get_text(strip=True) if duration_div else ""

		cat_div = w_link.find('div', class_='categories')
		categories = []
		if cat_div:
			cat_spans = cat_div.find_all('div', class_='category')
			categories = [c.get_text(strip=True) for c in cat_spans]
        
		workouts_dict[workout_title] = {
			"url": workout_url,
			"categories": categories,
			"duration": duration
		}
    
	logger.info(f"Found {len(workouts_dict)} workouts on program page.")
	return {
		"description_long": desc_long,
		"number_of_workouts": workouts_count,
		"workouts": workouts_dict
	}

def attempt_login(driver):
	"""
	If the login form is present, enter EMAIL and PASSWORD
	in the input fields and press the login button.
	Then wait for the account button to confirm success.
	"""
	# We'll look for the email field. If it is present, presumably the login page is shown.
	try:
		email_input = WebDriverWait(driver, 5).until(
			EC.presence_of_element_located((By.ID, "email"))
		)
		logger.info("Login page detected. Attempting to log in...")

		# Enter email
		email_input.clear()
		email_input.send_keys(EMAIL)

		# Enter password
		password_input = driver.find_element(By.ID, "password")
		password_input.clear()
		password_input.send_keys(PASSWORD)

		# Click login
		login_button = driver.find_element(By.ID, "submit-button")
		login_button.click()

		# Wait for account button to show up with title="Account" or id ~ "headlessui-menu-button..."
		WebDriverWait(driver, 15).until(
			EC.presence_of_element_located((By.CSS_SELECTOR, "button[title='Account']"))
		)
		logger.info("Successfully logged in!")
	except Exception as e:
		# It's possible login page isn't shown or something else occurred
		logger.info("No login form detected, or login step is not required.")

def main():
	# No command line arguments for email/password, removing cookies usage as requested
	logger.info("Starting Firefox.")
	firefox_options = Options()
	# Comment out headless to see the browser
	# firefox_options.add_argument("--headless")

	service = Service(GeckoDriverManager().install())
	driver = None

	try:
		driver = webdriver.Firefox(service=service, options=firefox_options)
		#driver.maximize_window()

		# 1) Navigate to main domain and see if we need to log in
		driver.get("https://my.lesmillsondemand.com/")
		attempt_login(driver)

		# 2) After logging in (or skipping if already logged in), move to "all-programs"
		base_url = "https://my.lesmillsondemand.com/all-programs/"
		driver.get(base_url)

		# Wait for main content
		WebDriverWait(driver, 15).until(
			EC.presence_of_all_elements_located((By.CLASS_NAME, 'albumCard'))
		)

		soup = get_dynamic_html_soup(driver)
		all_programs = scrape_all_programs_page(soup, base_url)

		# 3) For each program, gather details
		for program_title, program_info in all_programs.items():
			extra_data = scrape_program_page(driver, program_info["url"])
			all_programs[program_title]["description_long"] = extra_data["description_long"]
			all_programs[program_title]["number_of_workouts"] = extra_data["number_of_workouts"]
			all_programs[program_title]["workouts"] = extra_data["workouts"]

		# 4) Save as JSON
		output_filename = "lesmills_programs.json"
		with open(output_filename, "w", encoding="utf-8") as f:
			json.dump(all_programs, f, ensure_ascii=False, indent=2)
        
		logger.info(f"Scraping complete. Data saved to {output_filename}")
    
	except Exception as e:
		logger.exception("An error occurred during scraping.")
	finally:
		# Ensure the browser is always closed
		if driver:
			driver.quit()
			logger.info("Browser has been closed.")

if __name__ == "__main__":
	main()