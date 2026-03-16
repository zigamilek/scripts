import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------------ Configuration ------------------------ #

# User credentials
EMAIL = os.getenv("LES_MILLS_EMAIL")
PASSWORD = os.getenv("LES_MILLS_PASSWORD")

if not EMAIL or not PASSWORD:
	raise RuntimeError("Missing LES_MILLS_EMAIL or LES_MILLS_PASSWORD environment variable.")

# URLs
BASE_URL = "https://my.lesmillsondemand.com"
ALL_PROGRAMS_URL = f"{BASE_URL}/all-programs/"

# Output JSON file
OUTPUT_FILE = "les_mills_programs.json"

# Timeout settings
PAGE_LOAD_TIMEOUT = 30
ELEMENT_LOAD_TIMEOUT = 20

# ------------------------ Setup WebDriver ------------------------ #

# Initialize Firefox options (non-headless)
options = FirefoxOptions()
# Uncomment the next line to run in headless mode
# options.add_argument("--headless")

# Initialize the WebDriver
driver = webdriver.Firefox(options=options)

# Maximize the browser window
driver.maximize_window()

# Initialize WebDriverWait
wait = WebDriverWait(driver, ELEMENT_LOAD_TIMEOUT)

# ------------------------ Helper Functions ------------------------ #

def login():
	"""
	Logs into the Les Mills On Demand website using provided credentials.
	"""
	driver.get(BASE_URL + "/login")  # Adjust the login URL if different

	try:
		# Wait for email field to be present
		email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
		email_field.clear()
		email_field.send_keys(EMAIL)

		# Wait for password field to be present
		password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
		password_field.clear()
		password_field.send_keys(PASSWORD)

		# Wait for login button and click it
		login_button = wait.until(EC.element_to_be_clickable((By.ID, "submit-button")))
		login_button.click()

		# Wait for the account button to ensure login was successful
		wait.until(EC.presence_of_element_located((By.XPATH, "//button[@title='Account']")))

		print("Login successful.")

	except Exception as e:
		print("An error occurred during login:", e)
		driver.quit()
		exit(1)

def scrape_programs():
	"""
	Scrapes all fitness programs from the All Programs page.
	Returns a dictionary with program titles as keys and their details as values.
	"""
	driver.get(ALL_PROGRAMS_URL)

	try:
		# Wait for program cards to load
		program_cards = wait.until(EC.presence_of_all_elements_located(
			(By.XPATH, "//div[contains(@class, 'MuiGrid-grid-xs') and @role='listitem']")
		))

		print(f"Found {len(program_cards)} program cards.")

		programs_data = {}

		for card in program_cards:
			try:
				# Extract the anchor tag within the card
				link = card.find_element(By.TAG_NAME, "a")
				title = link.find_element(By.CLASS_NAME, "card--title").text.strip()
				description_short = link.find_element(By.CLASS_NAME, "card--description").text.strip()
				relative_url = link.get_attribute("href")
				program_url = relative_url if relative_url.startswith("http") else BASE_URL + relative_url

				# Initialize program data
				programs_data[title] = {
					"description_short": description_short,
					"url": program_url
				}

				print(f"Scraped program: {title}")

			except Exception as e:
				print(f"Failed to scrape a program card: {e}")

		return programs_data

	except Exception as e:
		print("An error occurred while scraping programs:", e)
		driver.quit()
		exit(1)

def scrape_program_details(programs):
	"""
	For each program, scrape additional details and workouts.
	Updates the programs dictionary in-place.
	"""
	for title, details in programs.items():
		program_url = details["url"]
		print(f"\nScraping details for program: {title}")
        
		try:
			driver.get(program_url)

			# Wait for description_long
			desc_long_elem = wait.until(EC.presence_of_element_located(
				(By.XPATH, "//div[contains(@class, 'desc--row')]/span")
			))
			description_long = desc_long_elem.text.strip()
			programs[title]["description_long"] = description_long

			# Wait for number_of_workouts
			workouts_elem = wait.until(EC.presence_of_element_located(
				(By.XPATH, "//p[contains(@class, 'styles__WorkoutResultsAmount')]")
			))
			number_of_workouts_text = workouts_elem.text.strip()
			number_of_workouts = int(''.join(filter(str.isdigit, number_of_workouts_text)))
			programs[title]["number_of_workouts"] = number_of_workouts

			print(f"Description Long: {description_long}")
			print(f"Number of Workouts: {number_of_workouts}")

			# Scrape workouts
			workouts = {}

			# Find all workout cards
			workout_cards = driver.find_elements(By.XPATH, "//a[contains(@class, 'videoCard')]")
			print(f"Found {len(workout_cards)} workouts for program '{title}'.")

			for workout_card in workout_cards:
				try:
					workout_title_elem = workout_card.find_element(By.CLASS_NAME, "title")
					workout_title = workout_title_elem.text.strip()

					relative_workout_url = workout_card.get_attribute("href")
					workout_url = relative_workout_url if relative_workout_url.startswith("http") else BASE_URL + relative_workout_url

					# Duration
					duration_elem = workout_card.find_element(By.CLASS_NAME, "duration")
					duration = duration_elem.text.strip()

					# Categories
					categories_elems = workout_card.find_elements(By.XPATH, ".//div[@class='categories']/div[@class='category']")
					categories = [cat.text.strip() for cat in categories_elems]

					# Add workout data
					workouts[workout_title] = {
						"url": workout_url,
						"categories": categories,
						"duration": duration
					}

					print(f"  Scraped workout: {workout_title}")

				except Exception as e:
					print(f"  Failed to scrape a workout card: {e}")

			programs[title]["workouts"] = workouts

		except Exception as e:
			print(f"An error occurred while scraping program '{title}': {e}")

def save_to_json(data, filename):
	"""
	Saves the data dictionary to a JSON file.
	"""
	try:
		with open(filename, "w", encoding="utf-8") as f:
			json.dump(data, f, indent=4, ensure_ascii=False)
		print(f"\nData successfully saved to {filename}")
	except Exception as e:
		print(f"Failed to save data to JSON: {e}")

# ------------------------ Main Execution ------------------------ #

if __name__ == "__main__":
	try:
		# Step 1: Login
		login()

		# Step 2: Scrape all programs
		programs = scrape_programs()

		# Step 3: Scrape details for each program
		scrape_program_details(programs)

		# Step 4: Save data to JSON
		save_to_json(programs, OUTPUT_FILE)

	finally:
		# Close the browser after completion
		driver.quit()
