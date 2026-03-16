from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import (
	NoSuchElementException,
	TimeoutException,
	ElementClickInterceptedException,
	StaleElementReferenceException,
	WebDriverException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def setup_driver(headless=True):
	"""
	Set up the Selenium WebDriver for Firefox with optional headless mode.
	Sets the window size programmatically to avoid misinterpretation of command-line arguments.
	"""
	firefox_options = Options()
	if headless:
		firefox_options.add_argument("--headless")
	firefox_options.add_argument("--start-maximized")
	firefox_options.add_argument("--disable-gpu")
	firefox_options.add_argument("--no-sandbox")
    
	# Initialize the Firefox driver (ensure geckodriver is in PATH)
	service = FirefoxService()  # If geckodriver is not in PATH, specify executable_path
	driver = webdriver.Firefox(service=service, options=firefox_options)
	driver.implicitly_wait(10)  # Implicit wait

	# Set window size programmatically
	driver.set_window_size(1920, 1080)
	return driver

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
		print("Clicked 'Reject All' for cookies.")
	except TimeoutException:
		print("Cookie consent dialog not found or already handled.")
	except Exception as e:
		print(f"Error clicking 'Reject All' button: {e}")

def scroll_to_load_up_to(driver, target_index, scroll_pause_time=1):
	"""
	Scrolls the page incrementally until at least target_index + 1 cards are loaded.
	If no new content is loaded after scrolling, scroll up and down slightly to trigger loading.
	"""
	SCROLL_INCREMENT = 3000  # Pixels to scroll each time
	total_cards = 0
	last_height = driver.execute_script("return document.body.scrollHeight")
	retries = 0
	max_retries = 5  # To prevent infinite scrolling
    
	while total_cards <= target_index and retries < max_retries:
		# Scroll down by SCROLL_INCREMENT pixels
		try:
			print(f"Scrolling down by {SCROLL_INCREMENT} pixels.")
			driver.execute_script(f"window.scrollBy(0, {SCROLL_INCREMENT});")
		except Exception as e:
			print(f"Error during scrolling: {e}")
			break
		time.sleep(scroll_pause_time)
        
		# Update the total number of loaded cards
		try:
			cards = driver.find_elements(By.CSS_SELECTOR, "div.PageStyled__HitCardContainer-sc-c1bey9-4")
			total_cards = len(cards)
			print(f"Total cards loaded: {total_cards}")
		except Exception as e:
			print(f"Error fetching card elements: {e}")
			break
        
		# Check if new content has been loaded
		try:
			new_height = driver.execute_script("return document.body.scrollHeight")
		except Exception as e:
			print(f"Error fetching scroll height: {e}")
			break
        
		if new_height == last_height:
			retries += 1
			print(f"No new content loaded. Retry {retries}/{max_retries}")
			if retries >= max_retries:
				print("Reached maximum scroll retries. Stopping scrolling.")
				break
			# Scroll up slightly to trigger loading
			try:
				print("Scrolling up by 500 pixels to trigger loading.")
				driver.execute_script("window.scrollBy(0, -500);")
				time.sleep(scroll_pause_time)
				print("Scrolling down by 500 pixels to continue loading.")
				driver.execute_script("window.scrollBy(0, 500);")
			except Exception as e:
				print(f"Error during corrective scrolling: {e}")
				break
			time.sleep(scroll_pause_time)
		else:
			last_height = new_height
			retries = 0  # Reset retries if new content is loaded

def collect_all_cards(driver, wait, target_count=144):
	"""
	Collects all program card WebElements after ensuring all are loaded.
	Returns a list of WebElement references.
	"""
	try:
		# Initial scroll to load up to target_count
		scroll_to_load_up_to(driver, target_count - 1)
        
		# After scrolling, fetch all card elements
		cards = driver.find_elements(By.CSS_SELECTOR, "div.PageStyled__HitCardContainer-sc-c1bey9-4")
		print(f"Total cards found: {len(cards)}")
        
		if len(cards) < target_count:
			print(f"Warning: Expected {target_count} cards, but found {len(cards)}.")
        
		return cards[:target_count]  # Ensure only target_count are processed
	except Exception as e:
		print(f"Error during collecting card identifiers: {e}")
		return []

def is_error_page(driver):
	"""
	Checks if the current page is an error page.
	Returns True if it is, False otherwise.
	"""
	current_url = driver.current_url
	if "about:neterror" in current_url or "1920,1080" in current_url:
		return True
	return False

def get_program_links(driver, wait, target_url, target_count=144):
	"""
	Iterates through each card by index, clicks it to navigate, captures the URL, and navigates back.
	Returns a list of collected URLs.
	"""
	collected_urls = []
    
	for index in range(target_count):
		try:
			print(f"\nProcessing card {index + 1}/{target_count}")
            
			# Scroll to load up to the current card
			scroll_to_load_up_to(driver, index)
            
			# Re-fetch the cards list
			cards = driver.find_elements(By.CSS_SELECTOR, "div.PageStyled__HitCardContainer-sc-c1bey9-4")
            
			if index >= len(cards):
				print(f"Card index {index} is out of range. Skipping.")
				continue
            
			card = cards[index]
            
			# Scroll the card into view
			try:
				driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
				time.sleep(0.5)  # Small delay to ensure the card is in view
			except Exception as e:
				print(f"Error scrolling card {index + 1} into view: {e}")
				continue
            
			# Click the card
			try:
				card.click()
				print(f"Clicked on card {index + 1}.")
			except (ElementClickInterceptedException, WebDriverException) as e:
				print(f"Error clicking on card {index + 1}: {e}")
				continue
            
			# Wait until the URL changes to the new page
			try:
				wait.until(EC.url_changes(target_url))
			except TimeoutException:
				print(f"Timeout waiting for URL to change after clicking card {index + 1}.")
				continue
            
			# Check if navigated to an error page
			if is_error_page(driver):
				print(f"Encountered an error page after clicking card {index + 1}. Skipping.")
				# Navigate back to the main page
				driver.get(target_url)
				wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.PageStyled__HitCardContainer-sc-c1bey9-4")))
				time.sleep(1)
				continue
            
			# Get the current URL
			current_url = driver.current_url
			print(f"Collected URL: {current_url}")
			collected_urls.append(current_url)
            
			# Navigate back to the main page using driver.get(target_url)
			try:
				driver.get(target_url)
				print(f"Navigated back to the main page after processing card {index + 1}.")
			except Exception as e:
				print(f"Error navigating back to the main page after processing card {index + 1}: {e}")
				continue
            
			# Wait until the main page is loaded again
			try:
				wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.PageStyled__HitCardContainer-sc-c1bey9-4")))
				time.sleep(1)  # Small delay to ensure the page is fully loaded
			except TimeoutException:
				print(f"Timeout waiting for main page to load after processing card {index + 1}.")
				continue
			except Exception as e:
				print(f"Error waiting for main page to load after processing card {index + 1}: {e}")
				continue
            
		except (NoSuchElementException, StaleElementReferenceException) as e:
			print(f"Error processing card {index + 1}: {e}")
			continue
    
	return collected_urls

def main():
	target_url = "https://www.beachbodyondemand.com/search/programs?sortBy=popularity&locale=en_US"
	driver = setup_driver(headless=False)  # Set headless=True to run without opening a browser window
	wait = WebDriverWait(driver, 20)
    
	try:
		driver.get(target_url)
		print("Navigated to the target URL.")
        
		# Handle cookie consent
		click_reject_all_cookies(driver, wait)
        
		# Collect all program cards
		initial_cards = collect_all_cards(driver, wait, target_count=144)
        
		if not initial_cards:
			print("No cards found. Exiting.")
			return
        
		# Collect unique URLs by interacting with each card
		program_links = get_program_links(driver, wait, target_url, target_count=144)
        
		# Remove duplicates if any
		unique_program_links = list(dict.fromkeys(program_links))
        
		# Verify if 144 links were collected
		if len(unique_program_links) < 144:
			print(f"\nWarning: Expected 144 links, but collected {len(unique_program_links)}.")
		else:
			print(f"\nSuccessfully collected {len(unique_program_links)} program links.")
        
		# Optionally, write the links to a file
		with open("program_links.txt", "w") as f:
			for link in unique_program_links:
				f.write(link + "\n")
        
		print("Program links have been written to 'program_links.txt'.")
    
	except Exception as e:
		print(f"An unexpected error occurred: {e}")
    
	finally:
		driver.quit()
		print("WebDriver has been closed.")

if __name__ == "__main__":
	main()
