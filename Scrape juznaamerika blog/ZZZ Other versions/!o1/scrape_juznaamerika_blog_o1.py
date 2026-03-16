import os
import re
import requests
from bs4 import BeautifulSoup
import frontmatter
from urllib.parse import urljoin, urlparse
from datetime import datetime

BASE_URL = "https://juznaamerika.travellerspoint.com"
TOC_URL = f"{BASE_URL}/toc/"
HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
		"AppleWebKit/537.36 (KHTML, like Gecko) "
		"Chrome/58.0.3029.110 Safari/537.3"
	)
}

def fetch_html(url):
	"""Fetch HTML from the given URL with a custom User-Agent."""
	print(f"[DEBUG] Fetching URL: {url}")
	r = requests.get(url, headers=HEADERS)
	r.raise_for_status()
	return r.text

def parse_toc(html):
	"""
	Parse the HTML of the TOC page or snippet.
	Return a list of dicts with keys: url, title, post_date.
	post_date is stored as a string 'YYYY-MM-DD' that we can later parse or sort lexically.
	"""
	print("[DEBUG] Parsing Table of Contents HTML...")
	soup = BeautifulSoup(html, "html.parser")

	# Identify the table by id or class
	table = soup.find("table", {"id": "table_of_contents"})
	if not table:
		table = soup.find("table", class_="sortable")

	if not table:
		print("[DEBUG] Could not find the expected table.")
		print(html[:500])  # show partial HTML for debugging
		return []

	# The table might not have <thead>/<tbody>, so let's just grab all <tr> directly.
	all_rows = table.find_all("tr", recursive=False)
	# Typically the first row is headers.
	if len(all_rows) <= 1:
		print("[DEBUG] No data rows found in the table.")
		return []

	data_rows = all_rows[1:]
	entries = []

	for row in data_rows:
		cols = row.find_all("td")
		if len(cols) < 2:
			continue

		link_tag = cols[0].find("a")
		if not link_tag:
			continue

		relative_url = link_tag.get("href")
		if relative_url.startswith("/"):
			post_url = BASE_URL + relative_url
		else:
			post_url = relative_url

		post_title = link_tag.get_text(strip=True)

		date_cell = cols[1]
		# The date might be in sorttable_customkey="YYYY-MM-DD HH:MM:SS"
		date_attr = date_cell.get("sorttable_customkey")
		if date_attr:
			# Example: "2008-07-31 11:27:54"
			# We'll just parse the date portion:
			dt_parts = date_attr.split(" ")
			post_date_str = dt_parts[0]  # "2008-07-31"
		else:
			# fallback: textual cell content
			post_date_str = date_cell.get_text(strip=True)

		entries.append({
			"url": post_url,
			"title": post_title,
			"post_date": post_date_str  # keep as string "YYYY-MM-DD"
		})
		print(f"[DEBUG] Found TOC entry => URL: {post_url}, Title: {post_title}, Date: {post_date_str}")

	return entries

def download_images_and_update_srcs(content_div, post_folder):
	"""
	Given the 'content_div' for a blog entry (BeautifulSoup tag),
	find all <img> tags, download them, and update their src to local paths.
    
	'post_folder' is the output folder for that specific post's assets.
	Returns an updated HTML string (not just text) so we keep any formatting + images.
	"""
	if not content_div:
		return ""

	# We'll keep the HTML but modify <img src="..."> in-place
	for img_tag in content_div.find_all("img"):
		original_src = img_tag.get("src")
		if not original_src:
			continue

		# Turn the src into an absolute URL if it's relative
		img_url = urljoin(BASE_URL, original_src)
		print(f"[DEBUG] Found image: {img_url}")

		# Download the image
		img_data = None
		try:
			resp = requests.get(img_url, headers=HEADERS)
			resp.raise_for_status()
			img_data = resp.content
		except Exception as e:
			print(f"[DEBUG] Could not download image {img_url}: {e}")
			continue

		# Create a local "images" folder inside the post folder
		images_folder = os.path.join(post_folder, "images")
		if not os.path.exists(images_folder):
			os.makedirs(images_folder)

		# Extract a filename from the URL (e.g. "something.jpg")
		parsed_url = urlparse(img_url)
		filename = os.path.basename(parsed_url.path)
		if not filename:
			# fallback if the URL doesn't have a proper path
			filename = f"image_{len(os.listdir(images_folder))}.jpg"

		local_path = os.path.join(images_folder, filename)

		with open(local_path, "wb") as f:
			f.write(img_data)

		# Update the <img src="..."> to a local relative path, e.g. "./images/filename.jpg"
		new_src = f"./images/{filename}"
		img_tag["src"] = new_src
		print(f"[DEBUG] Downloaded image => {local_path}")

	# Return the HTML (including updated <img src>)
	return str(content_div)

def parse_post_page(url, post_folder):
	"""
	Given a full URL to a blog entry, scrape the data:
	- Title (from h1.entrytitle)
	- Main content + images
	- Author (from the 'Posted by ...' snippet)
	- date_start, date_end, location (if found)
	- Comments
	Returns a dictionary with these fields.
	"""
	print(f"[DEBUG] Fetching post page: {url}")
	r = requests.get(url, headers=HEADERS)
	r.raise_for_status()
	soup = BeautifulSoup(r.text, "html.parser")

	# 1) Title
	entry_div = soup.find("div", class_="entry")
	if not entry_div:
		print("[DEBUG] Could not find <div class='entry'>. Possibly different structure.")
		return {}

	title_el = entry_div.find("h1", class_="entrytitle")
	if title_el:
		post_title = title_el.get_text(strip=True)
	else:
		post_title = "Untitled"

	print(f"[DEBUG] Post title found: {post_title}")

	# 2) Main content + images
	content_div = entry_div.find("div", class_="entrycontent")
	if content_div:
		# Download images and update <img src>
		updated_html = download_images_and_update_srcs(content_div, post_folder)
	else:
		print("[DEBUG] Could not find main content div with class='entrycontent'.")
		updated_html = ""

	# 3) Author + time posted (from <p class="entrydetails"> or similar)
	entry_details = entry_div.find("p", class_="entrydetails")
	author = None
	post_time = None
	if entry_details:
		author_link = entry_details.find("a")
		if author_link:
			author = author_link.get_text(strip=True)
		# We'll try to find a HH:MM pattern for time
		time_match = re.search(r"\b\d{1,2}:\d{2}\b", entry_details.get_text())
		if time_match:
			post_time = time_match.group(0)

	print(f"[DEBUG] Author: {author}, Post time (HH:MM): {post_time}")

	# 4) date_start, date_end, location
	#    The snippet doesn't show them, so we set them to None
	date_start = None
	date_end = None
	location = None

	# 5) Comments
	comments = []
	othercontent_div = soup.find("div", class_="othercontent")
	if othercontent_div:
		comment_divs = othercontent_div.find_all("div", class_="comment", recursive=False)
		for cdiv in comment_divs:
			paragraphs = cdiv.find_all("p", recursive=False)
			if len(paragraphs) >= 2:
				comment_text = paragraphs[0].get_text("\n", strip=True)
				author_par = paragraphs[1]
				author_link = author_par.find("a")
				comment_author = author_link.get_text(strip=True) if author_link else None
				comment_date = None  # snippet doesn't show comment date
				comments.append({
					"author": comment_author,
					"date": comment_date,
					"comment": comment_text
				})
			else:
				# fallback if structure differs
				comment_text = cdiv.get_text("\n", strip=True)
				comments.append({
					"author": None,
					"date": None,
					"comment": comment_text
				})
	else:
		print("[DEBUG] No <div class='othercontent'> found, so no comments extracted.")

	print(f"[DEBUG] Found {len(comments)} comments.")

	return {
		"title": post_title,
		# We'll store the updated HTML as the content (so that images are embedded).
		"content": updated_html,
		"author": author,
		"post_time": post_time,
		"date_start": date_start,
		"date_end": date_end,
		"location": location,
		"comments": comments
	}

def save_as_mdx(filename, metadata, content):
	"""Create an MDX file with python-frontmatter, using text mode."""
	post = frontmatter.Post(content)
	for key, value in metadata.items():
		post[key] = value

	mdx_string = frontmatter.dumps(post)
	with open(filename, "w", encoding="utf-8") as f:
		f.write(mdx_string)

	print(f"[DEBUG] Saved MDX file: {filename}")

def main():
	# 1) Fetch the real TOC
	toc_html = fetch_html(TOC_URL)

	# 2) Parse the table of contents
	entries = parse_toc(toc_html)

	# 3) Sort ascending by date
	#    'post_date' is a string "YYYY-MM-DD". 
	#    We can sort lexically or parse into datetime. Let's parse to be safe:
	def parse_yyyymmdd(date_str):
		# e.g. "2008-07-31"
		try:
			return datetime.strptime(date_str, "%Y-%m-%d")
		except ValueError:
			return datetime.min  # fallback if parse fails

	entries.sort(key=lambda x: parse_yyyymmdd(x["post_date"]))

	# 4) Create an output directory for MDX files
	out_dir = "mdx_posts"
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)
		print(f"[DEBUG] Created folder: {out_dir}")

	# 5) For each entry, scrape the page and produce the MDX
	for i, entry in enumerate(entries, start=1):
		url = entry["url"]
		title = entry["title"]
		post_date = entry["post_date"]

		# Construct a slug or safe name
		safe_title = "".join(c if c.isalnum() else "-" for c in title).strip("-")
		# We'll create a dedicated folder for this post, e.g. mdx_posts/0001-Polet-Lima-Pisco
		post_folder_name = f"{str(i).zfill(4)}-{safe_title}"
		post_folder = os.path.join(out_dir, post_folder_name)
		if not os.path.exists(post_folder):
			os.makedirs(post_folder)

		# Fetch details from the post page
		post_data = parse_post_page(url, post_folder)

		# Prepare the final .mdx filename
		mdx_filename = os.path.join(post_folder, "index.mdx")

		# Prepare front matter
		metadata = {
			"title": post_data.get("title", title),
			"post_date": post_date,
			"date_start": post_data["date_start"],
			"date_end": post_data["date_end"],
			"author": post_data["author"],
			"location": post_data["location"],
			# Comments as a list of dicts
			"comments": post_data["comments"],
		}

		# Save the MDX file with updated HTML content (with local image paths)
		content = post_data["content"]
		save_as_mdx(mdx_filename, metadata, content)

if __name__ == "__main__":
	main()
