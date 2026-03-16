import requests
from bs4 import BeautifulSoup
import frontmatter
import os
from datetime import datetime
import re

# Set up the user agent
headers = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def get_soup(url):
	print(f"Fetching content from: {url}")
	response = requests.get(url, headers=headers)
	return BeautifulSoup(response.content, 'html.parser')

def parse_toc(toc_url):
	soup = get_soup(toc_url)
	posts = []
    
	# Find all <tr> elements
	rows = soup.find_all('tr')
    
	for row in rows:
		title_elem = row.find('td', class_='title')
		date_elem = row.find('td', class_='entrydate')
        
		if title_elem and date_elem:
			title = title_elem.text.strip()
			date = date_elem.text.strip()
			link = title_elem.find('a')['href']
			posts.append({
				'title': title,
				'post_date': date,
				'link': f"https://juznaamerika.travellerspoint.com{link}"
			})
    
	print(f"Found {len(posts)} posts in the table of contents")
	return posts

def parse_post(post_url):
	soup = get_soup(post_url)
    
	content = soup.find('div', class_='entry')
	if content:
		content = content.text.strip()
	else:
		print(f"Warning: No content found for {post_url}")
		content = ""
    
	# Extract date_start, date_end, and location from the page source
	page_source = str(soup)
	date_start_match = re.search(r'"date_start":"(\d{4}-\d{2}-\d{2})"', page_source)
	date_end_match = re.search(r'"date_end":"(\d{4}-\d{2}-\d{2})"', page_source)
	location_match = re.search(r'"location":"([^"]+)"', page_source)
    
	date_start = date_start_match.group(1) if date_start_match else None
	date_end = date_end_match.group(1) if date_end_match else None
	location = location_match.group(1) if location_match else None
    
	# Extract comments
	comments = []
	comments_section = soup.find('div', id='comments')
	if comments_section:
		comment_divs = comments_section.find_all('div', class_='comment')
		for comment in comment_divs:
			author = comment.find('span', class_='author').text.strip()
			text = comment.find('div', class_='text').text.strip()
			comments.append(f"{author}: {text}")
    
	return content, date_start, date_end, location, comments

def create_mdx_file(post, content, date_start, date_end, location, comments):
	# Create frontmatter
	post_frontmatter = frontmatter.Post(content)
	post_frontmatter['title'] = post['title']
	post_frontmatter['post_date'] = post['post_date']
	post_frontmatter['date_start'] = date_start
	post_frontmatter['date_end'] = date_end
	post_frontmatter['author'] = "Ziga in Mateja"
	post_frontmatter['location'] = location
	post_frontmatter['comments'] = comments
    
	# Create filename
	filename = f"{post['post_date']}_{post['title'].replace(' ', '_')}.mdx"
    
	# Save the file
	with open(filename, 'w', encoding='utf-8') as f:
		f.write(frontmatter.dumps(post_frontmatter))
    
	print(f"Created MDX file: {filename}")

def main():
	toc_url = "https://juznaamerika.travellerspoint.com/toc/"
	posts = parse_toc(toc_url)
    
	for post in posts:
		content, date_start, date_end, location, comments = parse_post(post['link'])
		create_mdx_file(post, content, date_start, date_end, location, comments)

if __name__ == "__main__":
	main()