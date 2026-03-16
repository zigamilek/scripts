import os
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict
from dotenv import load_dotenv

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --------------------------- Configuration --------------------------- #

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

# User credentials
EMAIL = os.getenv("LES_MILLS_EMAIL")
PASSWORD = os.getenv("LES_MILLS_PASSWORD")

if not EMAIL or not PASSWORD:
    raise RuntimeError("Missing LES_MILLS_EMAIL or LES_MILLS_PASSWORD environment variable.")

# URL configurations
BASE_URL = "https://my.lesmillsondemand.com"
ALL_PROGRAMS_URL = f"{BASE_URL}/all-programs/"

# JSON output file
OUTPUT_FILE = "programs_data.json"

# Timeout settings
PAGE_LOAD_TIMEOUT = 30
ELEMENT_LOAD_TIMEOUT = 20

# --------------------------- Logging Setup --------------------------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("scraping.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# --------------------------- Data Classes --------------------------- #

@dataclass
class Workout:
    url: str
    duration: str

@dataclass
class Program:
    description_short: str
    url: str
    description_long: str = ""
    number_of_workouts: int = 0
    workouts: Dict[str, Workout] = None

# --------------------------- Helper Functions --------------------------- #

def initialize_webdriver():
    logger.info("Initializing Firefox WebDriver.")
    options = Options()
    options.headless = False  # Ensure browser is not headless
    driver = webdriver.Firefox(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver

def login(driver, email, password):
    logger.info("Navigating to the All Programs page.")
    driver.get(ALL_PROGRAMS_URL)

    try:
        logger.info("Waiting for the login page to appear.")
        WebDriverWait(driver, ELEMENT_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )

        logger.info("Entering email.")
        email_field = driver.find_element(By.XPATH, "//input[@type='email' and @name='email']")
        email_field.clear()
        email_field.send_keys(email)

        logger.info("Entering password.")
        password_field = driver.find_element(By.XPATH, "//input[@type='password' and @name='password']")
        password_field.clear()
        password_field.send_keys(password)

        logger.info("Clicking the Log In button.")
        login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
        login_button.click()

        logger.info("Waiting for login to complete.")
        # Using a partial match for the ID attribute as it may have dynamic parts
        WebDriverWait(driver, ELEMENT_LOAD_TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(@id, 'headlessui-menu-button')]"))
        )
        logger.info("Login successful.")
    except (NoSuchElementException, TimeoutException) as e:
        logger.error("An error occurred during login.", exc_info=True)
        driver.quit()
        raise e

def scrape_all_programs(driver) -> Dict[str, Program]:
    logger.info("Navigating to the All Programs page after login.")
    driver.get(ALL_PROGRAMS_URL)

    try:
        logger.info("Waiting for program cards to load.")
        WebDriverWait(driver, ELEMENT_LOAD_TIMEOUT).until(
            EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class, 'albumCard')]"))
        )
    except TimeoutException:
        logger.error("Program cards did not load in time.")
        driver.quit()
        raise

    logger.info("Extracting program data.")
    programs = {}
    program_elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'albumCard')]")

    for prog in program_elements:
        try:
            title_element = prog.find_element(By.XPATH, ".//span[contains(@class, 'card--title')]")
            title = title_element.text.strip()

            description_element = prog.find_element(By.XPATH, ".//span[contains(@class, 'card--description')]")
            description_short = description_element.text.strip()

            href = prog.get_attribute("href")
            url = href if href.startswith("http") else f"{BASE_URL}{href}"

            programs[title] = Program(
                description_short=description_short,
                url=url
            )
            logger.info(f"Scraped program: {title}")
        except NoSuchElementException:
            logger.warning("A program card is missing expected elements. Skipping.")
            continue

    logger.info(f"Total programs scraped: {len(programs)}")
    return programs

def scrape_program_details(driver, program: Program):
    logger.info(f"Scraping details for program: {program.url}")
    driver.get(program.url)

    try:
        logger.info("Waiting for description_long to load.")
        desc_element = WebDriverWait(driver, ELEMENT_LOAD_TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, 'desc--row')]//span")
            )
        )
        program.description_long = desc_element.text.strip()
        logger.info("Extracted description_long.")
    except TimeoutException:
        logger.error("description_long not found.", exc_info=True)

    # Find the footer banner link
    try:
        logger.info("Locating the footer banner link to workouts page.")
        # Using a partial match for the class attribute
        footer_banner = driver.find_element(
            By.XPATH, "//div[contains(@class, 'FixedBannerWrapper')]"
        )
        workouts_link = footer_banner.find_element(
            By.XPATH, ".//a[contains(@class, 'styles__Link')]"
        ).get_attribute("href")
        logger.info(f"Found workouts page link: {workouts_link}")
    except NoSuchElementException:
        logger.error("Footer banner link not found.", exc_info=True)
        return

    # Navigate to workouts page
    try:
        logger.info("Navigating to the workouts page.")
        driver.get(workouts_link)

        # Extract number_of_workouts from the specific element
        try:
            logger.info("Extracting number_of_workouts from the header.")
            workouts_header = WebDriverWait(driver, ELEMENT_LOAD_TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(@class, 'season-controls')]//h2[contains(text(), 'Workouts')]")
                )
            )
            number_of_workouts_text = workouts_header.text.strip()
            number_of_workouts = int(''.join(filter(str.isdigit, number_of_workouts_text)))
            program.number_of_workouts = number_of_workouts
            logger.info(f"Number of workouts (header): {number_of_workouts}")
        except (NoSuchElementException, TimeoutException, ValueError):
            logger.warning("Could not extract number_of_workouts from header.")

        # Scroll to the bottom to load all elements
        logger.info("Scrolling to the bottom to load all workouts.")
        scroll_pause_time = 2
        last_height = driver.execute_script("return document.body.scrollHeight")

        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # Extract number_of_workouts from the specific element after scrolling
        try:
            logger.info("Extracting number_of_workouts from the results amount element.")
            workouts_amount_element = driver.find_element(
                By.XPATH, "//p[contains(@class, 'WorkoutResultsAmount')]"
            )
            workouts_amount_text = workouts_amount_element.text.strip()
            number_of_workouts = int(''.join(filter(str.isdigit, workouts_amount_text)))
            program.number_of_workouts = number_of_workouts
            logger.info(f"Number of workouts (results amount): {number_of_workouts}")
        except (NoSuchElementException, ValueError):
            logger.warning("Could not extract number_of_workouts from results amount.")

        # Extract all workout cards
        try:
            logger.info("Extracting workout details.")
            # Using a more general XPath that matches any list item with 'collection-item' in its class
            workout_elements = driver.find_elements(
                By.XPATH, "//li[contains(@class, 'collection-item')]"
            )
            program.workouts = {}
            for workout in workout_elements:
                try:
                    title_element = workout.find_element(
                        By.XPATH, ".//div[contains(@class, 'browse-item-title')]//a//strong"
                    )
                    title = title_element.text.strip()

                    url = workout.find_element(By.XPATH, ".//a[contains(@class, 'browse-item-link')]").get_attribute("href")

                    duration_element = workout.find_element(
                        By.XPATH, ".//div[contains(@class, 'duration-container')]"
                    )
                    duration = duration_element.text.strip()

                    program.workouts[title] = Workout(
                        url=url,
                        duration=duration
                    )
                    logger.info(f"Scraped workout: {title}")
                except NoSuchElementException:
                    logger.warning("A workout card is missing expected elements. Skipping.")
                    continue
        except NoSuchElementException:
            logger.error("No workout elements found.", exc_info=True)

    except Exception as e:
        logger.error("An error occurred while scraping program details.", exc_info=True)

def main():
    driver = initialize_webdriver()

    try:
        login(driver, EMAIL, PASSWORD)

        programs = scrape_all_programs(driver)

        for title, program in programs.items():
            logger.info(f"Processing program: {title}")
            scrape_program_details(driver, program)
            # Optional: Add a short delay between processing programs
            time.sleep(2)

        # Convert dataclasses to dictionaries for JSON serialization
        programs_dict = {
            title: {
                "description_short": prog.description_short,
                "url": prog.url,
                "description_long": prog.description_long,
                "number_of_workouts": prog.number_of_workouts,
                "workouts": {
                    w_title: {
                        "url": workout.url,
                        "duration": workout.duration
                    }
                    for w_title, workout in (prog.workouts or {}).items()
                }
            }
            for title, prog in programs.items()
        }

        # Write to JSON file
        logger.info(f"Writing data to {OUTPUT_FILE}.")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(programs_dict, f, ensure_ascii=False, indent=4)
        logger.info("Data successfully written to JSON file.")

    except Exception as e:
        logger.error("An unexpected error occurred.", exc_info=True)
    finally:
        logger.info("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    main()
