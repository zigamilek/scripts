import os
import requests
from bs4 import BeautifulSoup
import frontmatter

# Adjust these constants as needed
BASE_URL = "https://juznaamerika.travellerspoint.com"
TOC_URL = f"{BASE_URL}/toc/"
HEADERS = {
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
				  "(KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}

def get_toc_entries():
	"""
	Scrape the table of contents page and return a list of
	(post_url, post_title, post_date, post_author).
	"""
	print(f"[DEBUG] Fetching table of contents from: {TOC_URL}")
	r = requests.get(TOC_URL, headers=HEADERS)
	r.raise_for_status()
	soup = BeautifulSoup(r.text, "html.parser")

	# Example selector guesses based on Travellerspoint structures
	# Each post might be in a div with a class like 'entryPanel'
	# Inside it, there's a link to the post, date, and author info
	entries = []
	entry_panels = soup.select("div.entryPanel")
	print(f"[DEBUG] Found {len(entry_panels)} entries in the TOC.")

	for panel in entry_panels:
		# Title and link
		title_el = panel.select_one("div.entryTitle a")
		if not title_el:
			continue  # skip if not found

		post_url = title_el.get("href")
		# If post_url is relative, combine with BASE_URL
		if post_url.startswith("/"):
			post_url = BASE_URL + post_url

		post_title = title_el.get_text(strip=True)

		# Author and Date might be in entrySubtitle or similar
		subtitle_el = panel.select_one("div.entrySubtitle")
		if subtitle_el:
			# Typical travellerspoint: "Ziga in Mateja posted on Jul 31, 2008"
			# We can attempt to parse the text. Or we find specific spans for date/author
			author_el = subtitle_el.select_one(".author")
			date_el = subtitle_el.select_one(".postDate")

			post_author = author_el.get_text(strip=True) if author_el else "Unknown"
			post_date = date_el.get_text(strip=True) if date_el else "Unknown"
		else:
			post_author = "Unknown"
			post_date = "Unknown"

		print(f"[DEBUG] TOC entry => Title: {post_title}, Date: {post_date}, Author: {post_author}, URL: {post_url}")
		entries.append((post_url, post_title, post_date, post_author))

	return entries

def parse_post_page(post_url):
	"""
	Given a post URL, scrape details:
	  - location, date_start, date_end
	  - post content
	  - comments
	Return a dict with all data.
	"""
	print(f"[DEBUG] Scraping post page: {post_url}")
	r = requests.get(post_url, headers=HEADERS)
	r.raise_for_status()
	soup = BeautifulSoup(r.text, "html.parser")

	# --- Parse location, date_start, date_end ---
	# These are often shown in a small details panel or table
	# Example guess: a table with th containing "Start", "End", "Location"
	date_start = None
	date_end = None
	location = None

	# Look for a table or info block that has trip info
	# e.g. <th>Start</th><td>Wednesday, 30 July 2008</td>
	#      <th>End</th><td>Thursday, 31 July 2008</td>
	#      <th>Location</th><td>Chile</td>
	info_rows = soup.select("table.entryDetails tr")
	for row in info_rows:
		header = row.select_one("th")
		value = row.select_one("td")
		if not header or not value:
			continue
		key_text = header.get_text(strip=True).lower()
		val_text = value.get_text(strip=True)
		if "start" in key_text:
			date_start = val_text
		elif "end" in key_text:
			date_end = val_text
		elif "location" in key_text:
			location = val_text

	print(f"[DEBUG] Found date_start={date_start}, date_end={date_end}, location={location}")

	# --- Parse the main post content ---
	# This might be inside an element with class "blogEntry" or similar
	content_div = soup.select_one("div.blogEntryContent")
	if not content_div:
		# fallback guess if the structure is different
		content_div = soup.select_one("div.entryContent")

	post_content_text = ""
	if content_div:
		# get textual content; you can refine this if you want HTML
		post_content_text = content_div.get_text("\n", strip=True)
	else:
		print("[DEBUG] Could not find main content div!")

	# --- Parse comments ---
	# Example guess: each comment in a div with class 'comment' or 'commentPanel'
	# The structure might be like:
	# <div class="comment">
	#   <div class="commentAuthor">Somebody said ...</div>
	#   <div class="commentDate">on X date</div>
	#   <div class="commentText">Lorem ipsum...</div>
	# </div>
	comments_list = []
	comment_divs = soup.select("div.comment")
	for cdiv in comment_divs:
		author_el = cdiv.select_one(".commentAuthor")
		date_el = cdiv.select_one(".commentDate")
		text_el = cdiv.select_one(".commentText")

		comment_author = author_el.get_text(strip=True) if author_el else "Anonymous"
		comment_date = date_el.get_text(strip=True) if date_el else "Unknown date"
		comment_text = text_el.get_text("\n", strip=True) if text_el else ""
        
		comments_list.append({
			"author": comment_author,
			"date": comment_date,
			"comment": comment_text
		})

	print(f"[DEBUG] Found {len(comments_list)} comments.")

	return {
		"date_start": date_start,
		"date_end": date_end,
		"location": location,
		"content": post_content_text,
		"comments": comments_list
	}

def save_as_mdx(filename, metadata, content):
	"""
	Create an MDX file from the given metadata and content
	using python-frontmatter.
	"""
	post = frontmatter.Post(content)
	for key, value in metadata.items():
		post[key] = value

	with open(filename, "w", encoding="utf-8") as f:
		frontmatter.dump(post, f)

	print(f"[DEBUG] Saved MDX file: {filename}")

def main():
	if not os.path.exists("mdx_posts"):
		os.makedirs("mdx_posts")
		print("[DEBUG] Created folder: mdx_posts")

	toc_entries = get_toc_entries()

	for i, (post_url, post_title, post_date, post_author) in enumerate(toc_entries, start=1):
		post_data = parse_post_page(post_url)

		# Create a slug or filename. For example:
		# "0001-pred-odhodom.mdx"
		# or just use the numeric index. You can refine as you wish.
		safe_title = "".join(c if c.isalnum() else "-" for c in post_title).strip("-")
		filename = f"mdx_posts/{str(i).zfill(4)}-{safe_title}.mdx"
        
		# Prepare the front matter
		mdx_metadata = {
			"title": post_title,
			"post_date": post_date,
			"date_start": post_data["date_start"],
			"date_end": post_data["date_end"],
			"author": post_author,
			"location": post_data["location"],
			"comments": post_data["comments"],
		}

		save_as_mdx(filename, mdx_metadata, post_data["content"])

if __name__ == "__main__":
	main()
