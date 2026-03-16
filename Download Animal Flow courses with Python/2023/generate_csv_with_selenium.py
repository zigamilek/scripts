import os
import re
import time
import csv
import yt_dlp
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

script_folder = os.path.dirname(os.path.realpath(__file__))
output_folder = '/Volumes/eulerShare/PaleoPrimal/0 Bodyweight Exercises/Videos/Mike Fitch/Animal Flow/On Demand/'
base_url = "https://ondemand.animalflow.com"

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

def main():
	# Initialize the driver
	print("Initializing the Firefox browser...")
	driver = webdriver.Firefox()
		
	# Log in
	login(driver)

	# Data to write to CSV
	data_to_write = []

	try:
		counter = 0  # Initialize the counter
		for i in range(1, 23):
			search_results_link = base_url + '/search_items?page_type=media&livestream=false&page=' + str(i)

			# Navigate to the URL
			driver.get(search_results_link)
			
			# Extract links to classes
			classes_links = get_class_links(driver, search_results_link)
				
			print("        Extracted class links:")
			for class_link in classes_links:
				counter += 1  # Increment the counter
				print(f"            {counter} - {class_link}")
					
				# Extract data about the class
				class_title, class_description, hls_url, categories_string = extract_class_data(driver, class_link)
									
				# Print hls_url
				print("                hls_url: " + hls_url)

				# Append the data to our list
				data_to_write.append([class_link, class_title, class_description, hls_url, categories_string])

	except KeyboardInterrupt:
		print("\nKeyboard interrupt detected! Saving data...")

	finally:
		filename = script_folder + "/scraped_data.csv"
		write_to_csv(filename, data_to_write)
		print(f"Data saved to {filename}")

		input("Press Enter to close the browser...")
		driver.quit()

def get_class_links(driver, url):
	# Navigate to the specified URL
	driver.get(url)

	# Wait 5 seconds
	time.sleep(5)

	# Scroll to the bottom of the page
	driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

	# Use Beautiful Soup to parse the page source
	soup = BeautifulSoup(driver.page_source, 'lxml')

	# Extract the relevant anchor elements
	class_elements = soup.select("li.mb-5 div.thumbnail__poster__overlay a.mx-1")

	# Extract the 'href' attributes (i.e., the URLs) from the found elements
	class_links = [base_url + element['href'].replace('?autoplay=true&progress=0', '') for element in class_elements]

	return class_links

def extract_class_data(driver, class_url):
	driver.get(class_url)

	# Use Beautiful Soup to parse the page source
	soup = BeautifulSoup(driver.page_source, 'lxml')

	# Extract the class title
	try:
		# Find the h1 tag
		h1_tag = soup.find('h1')

		# Remove all span and div tags and their content
		for element in h1_tag.find_all(['span', 'div']):
			element.decompose()

		# Get the cleaned text from the modified h1
		class_title = h1_tag.text.strip()
	except:
		class_title = 'No Title'

	# Extract the class description
	try:
		class_description_element = soup.select_one('div.description div.html_output')
	except:
		class_description_element = 'No Description'

	# Extract the categories
	try:
		categories = soup.select('div#media_has_category a.tax-ancestor-link')
		
		# Extract text content of each a element and join them into a |-separated string
		categories_list = [category.get_text().strip() for category in categories]
		categories_string = '|'.join(categories_list)
	except:
		categories_string = 'No Categories'

	# Extract the `src` attribute of the iframe with the class "video"
	try:
		iframe_element = driver.find_element(By.CSS_SELECTOR, "iframe.video")  # Locate the iframe with the class "video"

		src_value = base_url + iframe_element.get_attribute("src")

		# Switch to the iframe's context
		driver.switch_to.frame(iframe_element)

		# Store the HTML content of the iframe
		iframe_content = driver.page_source

		# Switch back to the main window's context
		driver.switch_to.default_content()

	except Exception as e:
		print(f"Error extracting the iframe content: {e}")

	# Extract hls_url from the iframe HTML using regex
	hls_url_pattern = re.compile(r'var hls_url = "(.*?)"')
	match = hls_url_pattern.search(iframe_content)

	if match:
		hls_url = match.group(1)
		return class_title, str(class_description_element).replace('\n', ' ').replace('\r', ''), hls_url, categories_string
	else:
		print("Failed to extract hls_url.")

def write_to_csv(filename, data):
	with open(filename, 'w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(["Class Link", "Class Title", "Class Description", "HLS URL", "Categories"]) # Write the header
		writer.writerows(data)

def login(driver):
	# Load .env file
	print("    Loading environment variables from .env file...")
	load_repo_dotenv()

	# Retrieve environment variables
	print("    Retrieving email and password from environment variables...")
	email = os.environ.get('EMAIL')
	password = os.environ.get('PASSWORD')

	if not email or not password:
		raise ValueError("Email or Password not found in environment variables!")

	# Navigate to the login page
	print("    Navigating to the login page...")
	driver.get("https://ondemand.animalflow.com/accounts/login/")

	# Locate the email and password fields
	print("    Locating email and password fields...")
	email_field = driver.find_element(By.ID, "CustomerEmail")
	password_field = driver.find_element(By.ID, "CustomerPassword")

	# Input your credentials
	print(f"    Entering credentials for email: {email}")  # Only displaying email for demonstration. Avoid printing sensitive info like passwords.
	email_field.send_keys(email)
	password_field.send_keys(password)

	# Locate the login button and click it
	print("    Locating and clicking the login button...")
	login_button = driver.find_element(By.XPATH, '//input[@value="Log In"]')
	login_button.click()

	print("    Login attempt completed!")

# source: https://stackoverflow.com/a/295466/1199569
def slugify(value):
	"""
	Normalizes string, converts to lowercase, removes non-alpha characters,
	and converts spaces to hyphens.
	"""
	import unicodedata
	value = unicodedata.normalize('NFKD', value).encode(
		'ascii', 'ignore').decode('utf-8')
	value = str(re.sub('[^\w\s-]', '', value).strip())
	value = str(re.sub('[-\s]+', '-', value))[0:100]
	# ...
	return value

if __name__ == "__main__":
	""" This is executed when run from the command line """
	main()