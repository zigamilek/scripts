import requests
from bs4 import BeautifulSoup
import frontmatter
import os
from urllib.parse import urljoin, urlparse
import re
import sys
from datetime import datetime

# Constants
TOC_URL = 'https://juznaamerika.travellerspoint.com/toc/'
BASE_URL = 'https://juznaamerika.travellerspoint.com/'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
HEADERS = {'User-Agent': USER_AGENT}
OUTPUT_DIR = 'mdx_posts'

# Create output directory if it doesn't exist
if not os.path.exists(OUTPUT_DIR):
	os.makedirs(OUTPUT_DIR)
	print(f"Created directory: {OUTPUT_DIR}")

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
		# Process images to ensure absolute URLs
		images = content_div.find_all('img')
		for img in images:
			src = img.get('src')
			if src:
				# Make sure the image URL is absolute
				img_url = urljoin(BASE_URL, src)
				img['src'] = img_url
				print(f"Image found and updated: {img_url}")

		# Optionally, process links to enlarge images to get full-size images
		enlarge_links = content_div.find_all('a', class_='enlarge_image')
		for a in enlarge_links:
			href = a.get('href')
			if href and 'src=' in href:
				parsed_href = urlparse(href)
				query = parsed_href.query
				src_match = re.search(r'src=(https?://[^&]+)', query)
				if src_match:
					full_image_url = src_match.group(1)
					# Replace the href with the full image URL
					a['href'] = full_image_url
					print(f"Enlarge image link updated to: {full_image_url}")

		# Convert the content to Markdown if desired
		# Here, we'll keep it as HTML
		content_html = str(content_div)
		front_matter['content'] = content_html
		print("Extracted post content.")
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

def save_mdx(front_matter, number):
	# Create a filename from the title or another unique identifier
	title_slug = re.sub(r'[^\w\s-]', '', front_matter['title']).strip().lower()
	title_slug = re.sub(r'[\s_-]+', '-', title_slug)
	filename = f"{number:03d}-{title_slug}.mdx"  # Zero-padded numbering
	filepath = os.path.join(OUTPUT_DIR, filename)

	# Prepare front matter fields
	fm = {
		'title': front_matter.get('title', ''),
		'post_date': front_matter.get('post_date', ''),
		'date_start': front_matter.get('date_start', ''),
		'date_end': front_matter.get('date_end', ''),
		'author': front_matter.get('author', ''),
		'location': front_matter.get('location', ''),
		'comments': front_matter.get('comments', [])
	}

	# Create the front matter and content
	post = frontmatter.Post(front_matter.get('content', ''), **fm)

	# Write to file using dumps to avoid bytes issue
	try:
		post_content = frontmatter.dumps(post)
		with open(filepath, 'w', encoding='utf-8') as f:
			f.write(post_content)
		print(f"Saved MDX file: {filepath}")
	except Exception as e:
		print(f"Error saving MDX file '{filepath}': {e}")

def main():
	print("Starting blog scraping...")

	# Scrape table of contents
	posts = scrape_toc(TOC_URL)
	print(f"Total posts to process: {len(posts)}")

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

	for idx, post in enumerate(posts_sorted, 1):
		print(f"\nProcessing post {idx}/{len(posts_sorted)}: {post['title']}")
		front_matter = scrape_post(post, post['post_date'])
		save_mdx(front_matter, idx)

	print("\nBlog scraping completed successfully.")

if __name__ == "__main__":
	main()
