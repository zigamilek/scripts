import requests
from bs4 import BeautifulSoup
import csv
import os
from urllib.parse import urljoin, urlparse
import re
import sys
from datetime import datetime
from markdownify import markdownify as md
import shutil
import json

# Constants
TOC_URL = 'https://juznaamerika.travellerspoint.com/toc/'
BASE_URL = 'https://juznaamerika.travellerspoint.com/'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
HEADERS = {'User-Agent': USER_AGENT}
OUTPUT_DIR = 'wordpress_export'
IMAGES_DIR = os.path.join(OUTPUT_DIR, 'images')
CSV_FILE = os.path.join(OUTPUT_DIR, 'wordpress_posts.csv')

# Create output and images directories if they don't exist
for directory in [OUTPUT_DIR, IMAGES_DIR]:
	if not os.path.exists(directory):
		os.makedirs(directory)
		print(f"Created directory: {directory}")

def get_soup(url):
	try:
		print(f"Fetching URL: {url}")
		response = requests.get(url, headers=HEADERS)
		response.raise_for_status()
		return BeautifulSoup(response.text, 'html.parser')
	except requests.RequestException as e:
		print(f"Error fetching {url}: {e}")
		sys.exit(1)

def scrape_toc(toc_url):
	soup = get_soup(toc_url)
	posts = []

	# Select the table with id="table_of_contents"
	toc_table = soup.find('table', id='table_of_contents')
	if not toc_table:
		print("No table with id 'table_of_contents' found.")
		print("Fetched HTML snippet (first 1000 characters):")
		print(soup.prettify()[:1000])  # Print the first 1000 characters for inspection
		return posts

	# Attempt to find tbody
	tbody = toc_table.find('tbody')
	if tbody:
		rows = tbody.find_all('tr')
		print("Found <tbody> in the TOC table.")
	else:
		# Sometimes tbody is not present; find all tr elements directly under the table
		rows = toc_table.find_all('tr')
		print("No <tbody> found. Found all <tr> directly under the table.")

	print(f"Total <tr> elements found: {len(rows)}")

	# Check if the first row is a header by looking for 'Title' in the first <th>
	first_row = rows[0] if rows else None
	if first_row and first_row.find('th'):
		print("First row is a header. Skipping it.")
		rows = rows[1:]
		print(f"Rows after skipping header: {len(rows)}")
	else:
		print("No header row detected.")

	for idx, row in enumerate(rows, start=1):
		try:
			cols = row.find_all('td')
			if len(cols) < 2:
				print(f"Row {idx} does not have enough columns. Skipping.")
				continue

			# First column: Post title and URL
			title_link = cols[0].find('a', href=True)
			if not title_link:
				print(f"Row {idx}: No anchor tag found in the first column. Skipping.")
				continue
			post_href = title_link['href']
			post_url = urljoin(BASE_URL, post_href)
			title = title_link.get_text(strip=True)
			print(f"Row {idx}: Post Title: {title}")
			print(f"Row {idx}: Post URL: {post_url}")

			# Second column: Post date from sorttable_customkey
			date_td = cols[1]
			post_date_str = date_td.get('sorttable_customkey', '').strip()
			if not post_date_str:
				print(f"Row {idx}: No sorttable_customkey found for post date. Skipping.")
				continue
			post_date = parse_date(post_date_str)
			print(f"Row {idx}: Post Date (from TOC): {post_date}")

			posts.append({
				'title': title,
				'url': post_url,
				'post_date': post_date
			})
		except Exception as e:
			print(f"Error parsing row {idx}: {e}")
			continue

	return posts

def parse_date(date_str):
	"""
	Parses date strings in the format 'YYYY-MM-DD HH:MM:SS' and returns 'YYYY-MM-DD'.
	"""
	try:
		dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
		return dt.strftime('%Y-%m-%d')
	except ValueError:
		print(f"Date format not recognized: {date_str}. Returning original string.")
		return date_str

def scrape_post(post, post_date):
	soup = get_soup(post['url'])
	front_matter = {}

	# Extract title
	title_tag = soup.find('h1', class_='entrytitle')
	if title_tag and title_tag.find('a'):
		title = title_tag.find('a').get_text(strip=True)
		front_matter['title'] = title
		print(f"Extracted Title: {title}")
	else:
		front_matter['title'] = post['title']
		print("Title tag not found. Using title from TOC.")

	# Assign post_date from TOC
	front_matter['post_date'] = post_date

	# Extract date_start and date_end from span.entrydate
	entrydate_span = soup.find('span', class_='entrydate')
	if entrydate_span:
		date_text = entrydate_span.get_text(strip=True)
		print(f"Raw entrydate text: '{date_text}'")
		date_start, date_end = parse_entrydate(date_text)
		front_matter['date_start'] = date_start
		front_matter['date_end'] = date_end
		print(f"Date Start: {date_start}")
		print(f"Date End: {date_end}")
	else:
		front_matter['date_start'] = None
		front_matter['date_end'] = None
		print("Entrydate span not found.")

	# Extract location from span.country_links > a
	country_links_span = soup.find('span', class_='country_links')
	if country_links_span and country_links_span.find('a'):
		location = country_links_span.find('a').get_text(strip=True)
		front_matter['location'] = location
		print(f"Location: {location}")
	else:
		front_matter['location'] = None
		print("Location not found.")

	# Extract author from p.entrydetails > a[href^="/author/"]
	entrydetails_p = soup.find('p', class_='entrydetails')
	author = "Unknown"
	if entrydetails_p:
		author_link = entrydetails_p.find('a', href=re.compile(r'^/author/'))
		if author_link:
			author = author_link.get_text(strip=True)
			print(f"Author: {author}")
	front_matter['author'] = author

	# Extract comments
	comments = []
	comments_div = soup.find('div', class_='othercontent')
	if comments_div:
		comment_divs = comments_div.find_all('div', class_='comment')
		print(f"Found {len(comment_divs)} comments.")
		for c_idx, comment_div in enumerate(comment_divs, start=1):
			try:
				comment_text_p = comment_div.find_all('p')[0]
				comment_text = comment_text_p.get_text(separator="\n", strip=True)
				comment_details_p = comment_div.find('p', class_='commentdetails')
				if comment_details_p and comment_details_p.find('a'):
					comment_author = comment_details_p.find('a').get_text(strip=True)
				else:
					comment_author = "Unknown"
				comments.append({
					'author': comment_author,
					'content': comment_text,
					# 'date': None  # No date available in comments
				})
				print(f"Comment {c_idx}: by {comment_author}")
			except Exception as e:
				print(f"Error parsing comment {c_idx}: {e}")
				continue
	front_matter['comments'] = comments

	# Extract content from div.entrycontent
	content_div = soup.find('div', class_='entrycontent')
	if content_div:
		# Process images to ensure absolute URLs and download them
		images = content_div.find_all('img')
		image_mappings = {}  # Original URL -> Local path
		for img in images:
			src = img.get('src')
			if src:
				# Make sure the image URL is absolute
				img_url = urljoin(BASE_URL, src)
				# Extract image filename
				parsed_url = urlparse(img_url)
				img_filename = os.path.basename(parsed_url.path)
				# Generate a safe slug from post title
				title_slug = re.sub(r'[^\w\s-]', '', front_matter['title']).strip().lower()
				title_slug = re.sub(r'[\s_-]+', '-', title_slug)
				# Ensure unique image filenames by prefixing with title slug
				img_unique_name = f"{title_slug}-{img_filename}"
				local_img_path = os.path.join('images', img_unique_name)
				full_local_img_path = os.path.join(IMAGES_DIR, img_unique_name)

				# Download the image if it doesn't already exist
				if not os.path.exists(full_local_img_path):
					try:
						print(f"Downloading image: {img_url}")
						img_response = requests.get(img_url, headers=HEADERS, stream=True)
						img_response.raise_for_status()
						with open(full_local_img_path, 'wb') as f:
							shutil.copyfileobj(img_response.raw, f)
						print(f"Saved image to: {full_local_img_path}")
					except requests.RequestException as e:
						print(f"Error downloading image {img_url}: {e}")
						continue

				# Update the img tag's src to the local image path
				img['src'] = local_img_path
				image_mappings[img_url] = local_img_path
				print(f"Image src updated to: {local_img_path}")

		# Remove enlarge_image links to ensure everything works offline
		enlarge_links = content_div.find_all('a', class_='enlarge_image')
		for a in enlarge_links:
			a.unwrap()  # Removes the <a> tag but keeps the inner content (the image)
			print("Removed enlarge_image link to ensure offline functionality.")

		# Convert the content to HTML (as WordPress accepts HTML)
		content_html = str(content_div)
		# Remove leading blank lines if any
		content_html = content_html.lstrip('\n')
		front_matter['content'] = content_html
		print("Converted post content to HTML.")
	else:
		front_matter['content'] = ""
		print("Post content not found.")

	return front_matter

def parse_entrydate(date_text):
	"""
	Parses the entrydate text to extract date_start and date_end.
	Expected formats:
	- "DD.MM.YYYY - DD.MM.YYYY"
	- "DD.MM.YYYY"
	Returns dates in "YYYY-MM-DD" format.
	"""
	try:
		if '-' in date_text:
			start_str, end_str = date_text.split('-')
			start_str = start_str.strip()
			end_str = end_str.strip()
			start_date = datetime.strptime(start_str, '%d.%m.%Y').strftime('%Y-%m-%d')
			end_date = datetime.strptime(end_str, '%d.%m.%Y').strftime('%Y-%m-%d')
			return start_date, end_date
		else:
			single_date = datetime.strptime(date_text, '%d.%m.%Y').strftime('%Y-%m-%d')
			return single_date, single_date
	except ValueError as e:
		print(f"Error parsing entrydate '{date_text}': {e}")
		return None, None

def save_to_csv(posts_data, csv_file):
	# Define CSV headers
	headers = [
		'Title',
		'Content',
		'Date',
		'Author',
		'Location',
		'Comments'
	]

	# Write to CSV
	try:
		with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
			writer = csv.DictWriter(csvfile, fieldnames=headers)
			writer.writeheader()
			for post in posts_data:
				# Prepare comments as a JSON string
				comments_json = json.dumps(post['comments'], ensure_ascii=False)
                
				writer.writerow({
					'Title': post['title'],
					'Content': post['content'],
					'Date': post['post_date'],
					'Author': post['author'],
					'Location': post['location'] if post['location'] else '',
					'Comments': comments_json
				})
		print(f"\nSuccessfully saved all posts to CSV: {csv_file}")
	except Exception as e:
		print(f"Error writing to CSV file '{csv_file}': {e}")

def main():
	print("Starting blog scraping...")

	# Scrape table of contents
	posts = scrape_toc(TOC_URL)
	print(f"Total posts found: {len(posts)}")

	if not posts:
		print("No posts found. Exiting.")
		sys.exit(0)

	# Sort posts by post_date ascending
	# Handle cases where post_date might not be in 'YYYY-MM-DD' format
	def sort_key(post):
		try:
			return datetime.strptime(post['post_date'], '%Y-%m-%d')
		except ValueError:
			return datetime.min  # Push invalid dates to the start

	posts_sorted = sorted(posts, key=sort_key)

	# Scrape each post
	for idx, post in enumerate(posts_sorted, 1):
		print(f"\nProcessing post {idx}/{len(posts_sorted)}: {post['title']}")
		front_matter = scrape_post(post, post['post_date'])
		# Add scraped data to post dict
		post.update(front_matter)

	# Save all posts data to CSV
	save_to_csv(posts_sorted, CSV_FILE)

	print("\nBlog scraping and CSV generation completed successfully.")

if __name__ == "__main__":
	main()
