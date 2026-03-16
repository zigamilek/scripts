import os
import re
import requests
from bs4 import BeautifulSoup
import frontmatter

BASE_URL = "https://juznaamerika.travellerspoint.com"
TOC_URL = f"{BASE_URL}/toc/"  # for reference, though we’ll parse the snippet if needed
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
	print("[DEBUG] Parsing Table of Contents HTML...")
	soup = BeautifulSoup(html, "html.parser")

	table = soup.find("table", {"id": "table_of_contents"})
	# If you need a fallback:
	if not table:
		table = soup.find("table", class_="sortable")

	if not table:
		print("[DEBUG] Could not find the table.")
		print(html[:500])  # print the first 500 characters to debug
		return []

	# Instead of finding <tbody>, just get all rows.
	all_rows = table.find_all("tr", recursive=False)
	print(f"[DEBUG] Found {len(all_rows)} <tr> elements in the table.")

	# Usually, the first row contains the <th> headers
	if len(all_rows) <= 1:
		print("[DEBUG] No data rows found in the table.")
		return []

	# So skip the header row by slicing [1:]
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
		# The date might be in `sorttable_customkey`:
		date_attr = date_cell.get("sorttable_customkey")
		if date_attr and " " in date_attr:
			# if "2008-07-31 11:27:54", split off "YYYY-MM-DD"
			post_date = date_attr.split(" ")[0]
		else:
			# fallback: just extract text from the cell
			post_date = date_cell.get_text(strip=True)

		entries.append({
			"url": post_url,
			"title": post_title,
			"post_date": post_date
		})
			
		print(f"[DEBUG] Found TOC entry => URL: {post_url}, Title: {post_title}, Date: {post_date}")

	return entries

def parse_post_page(url):
	"""
	Given a full URL to a blog entry, scrape the data:
	- Title (from h1.entrytitle)
	- Main content (from div.entrycontent)
	- Author (from the 'Posted by ...' snippet)
	- date_start, date_end, location (if found somewhere)
	- Comments
	Returns a dictionary with these fields.
	"""
	html = fetch_html(url)
	soup = BeautifulSoup(html, "html.parser")

	# 1) Title
	entry_div = soup.find("div", class_="entry")
	if not entry_div:
		print("[DEBUG] Could not find <div class='entry'>. Possibly different structure.")
		return {}

	title_el = entry_div.find("h1", class_="entrytitle")
	if title_el:
		# the text might be in <a> inside the h1
		post_title = title_el.get_text(strip=True)
	else:
		post_title = "Untitled"

	print(f"[DEBUG] Post title found: {post_title}")

	# 2) Main content
	content_div = entry_div.find("div", class_="entrycontent")
	if content_div:
		# If you want the HTML content, use str(content_div)
		# If you want plain text, use get_text
		post_content = content_div.get_text("\n", strip=True)
	else:
		post_content = ""
		print("[DEBUG] Could not find main content div with class='entrycontent'.")

	# 3) Author + time posted (from <p class="entrydetails"> or similar)
	#    Example snippet: <p class="entrydetails">Posted by <a ...>bjelakrez</a> <a>06:37</a></p>
	entry_details = entry_div.find("p", class_="entrydetails")
	author = None
	post_time = None
	if entry_details:
		author_link = entry_details.find("a")
		if author_link:
			author = author_link.get_text(strip=True)
		# There's also a time "06:37" in plain text or in a second <a>
		# We'll attempt to find any HH:MM in the text as an example.
		time_match = re.search(r"\b\d{1,2}:\d{2}\b", entry_details.get_text())
		if time_match:
			post_time = time_match.group(0)
	else:
		print("[DEBUG] No <p class='entrydetails'> found. Author/time unknown.")

	print(f"[DEBUG] Author: {author}, Post time (HH:MM): {post_time}")

	# 4) date_start, date_end, location
	#    The snippet provided does not show any explicit fields for these,
	#    so here we do a placeholder parse or set them to None.
	#    In your real HTML, you might have them in a table, meta tags, etc.
	#    For example:
	date_start = None
	date_end = None
	location = None

	# 5) Comments
	#    The snippet for comments is within <div class="othercontent"><h2 id="comments">...
	#    Each comment is in <div class="comment"> with first <p> as text and second <p> as author details.
	comments = []
	othercontent_div = soup.find("div", class_="othercontent")
	if othercontent_div:
		comment_divs = othercontent_div.find_all("div", class_="comment", recursive=False)
		for cdiv in comment_divs:
			paragraphs = cdiv.find_all("p", recursive=False)
			if len(paragraphs) >= 2:
				# The first paragraph is the comment text
				comment_text = paragraphs[0].get_text("\n", strip=True)
				# The second paragraph has the author in class "commentdetails"
				comment_author = None
				author_par = paragraphs[1]
				author_link = author_par.find("a")
				if author_link:
					comment_author = author_link.get_text(strip=True)
				# The snippet shows no date in each comment, so set None or skip
				comment_date = None

				comments.append({
					"author": comment_author,
					"date": comment_date,
					"comment": comment_text
				})
			else:
				# If the structure differs or there's only one <p>
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
		"content": post_content,
		"author": author,
		"post_time": post_time,
		"date_start": date_start,
		"date_end": date_end,
		"location": location,
		"comments": comments
	}

def save_as_mdx(filename, metadata, content):
	post = frontmatter.Post(content)
	for key, value in metadata.items():
		post[key] = value

	mdx_string = frontmatter.dumps(post)

	with open(filename, "w", encoding="utf-8") as f:
		f.write(mdx_string)

	print(f"[DEBUG] Saved MDX file: {filename}")

def main():
	# Example approach: we can fetch the real TOC URL or just parse your snippet.
	# 1) If you want to parse the real table-of-contents page from the live site:
	#    toc_html = fetch_html(TOC_URL)
	#
	# 2) Otherwise, if you have the snippet in a local file or string, parse that.

	# For demonstration, let's assume we do it from the live site:
	#   (Adjust or remove if you'd rather parse a local snippet.)
	# ---
	toc_html = fetch_html(TOC_URL)

	# Parse the table of contents to get entries
	entries = parse_toc(toc_html)

	# Create an output directory for MDX files
	out_dir = "mdx_posts"
	if not os.path.exists(out_dir):
		os.makedirs(out_dir)
		print(f"[DEBUG] Created folder: {out_dir}")

	# For each entry, scrape the page and produce the MDX
	for i, entry in enumerate(entries, start=1):
		url = entry["url"]
		title = entry["title"]
		post_date = entry["post_date"]  # from table_of_contents attribute

		post_data = parse_post_page(url)

		# Construct a safe filename
		# For example, "0001-pred-odhodom.mdx"
		safe_title = "".join(c if c.isalnum() else "-" for c in title).strip("-")
		filename = f"{out_dir}/{str(i).zfill(4)}-{safe_title}.mdx"

		# Prepare front matter
		metadata = {
			"title": post_data.get("title", title),
			"post_date": post_date,
			# If you do have additional date/time logic from the post page, you can incorporate it here:
			"date_start": post_data["date_start"],
			"date_end": post_data["date_end"],
			"author": post_data["author"],
			"location": post_data["location"],
			# Comments as a list of dicts
			"comments": post_data["comments"],
		}

		# Use the content from the post
		content = post_data["content"]

		# Save the MDX file
		save_as_mdx(filename, metadata, content)

if __name__ == "__main__":
	main()
