import requests
from bs4 import BeautifulSoup
import frontmatter
import os
import re
from datetime import datetime
import html2text
from urllib.parse import urljoin

# Set the User-Agent for the requests
HEADERS = {
	'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

BASE_URL = "https://juznaamerika.travellerspoint.com"

def get_soup(url):
	print(f"Fetching URL: {url}")
	response = requests.get(url, headers=HEADERS)
	print(f"Requested URL: {url}, Status Code: {response.status_code}")  # Debug print
	response.raise_for_status()
	return BeautifulSoup(response.content, 'html.parser')

def scrape_toc():
	toc_url = f"{BASE_URL}/toc/"
	soup = get_soup(toc_url)
    
	# Extract the links to individual blog posts and their dates
	post_links = soup.select('table tr')
	print(f"Found {len(post_links)} post links\n")  # Debug print

	posts = []
	for i, row in enumerate(post_links):
		link = row.find('a')
		date_element = row.find('td', width="150px")
        
		if not link or not date_element:
			print(f"    Skipping row {i+1} due to missing link or date")  # Debug print
			continue

		post_url = f"{BASE_URL}{link['href']}"
		date = date_element['sorttable_customkey']
		title = link.get_text().strip()
		print(f"    Processing post {i+1}/{len(post_links)}: {post_url}, Date: {date}, Title: {title}")  # Debug print
		posts.append((title, post_url, date))

	print(f"Total posts found: {len(posts)}")
	return posts

def download_image(url, folder):
	if not os.path.exists(folder):
		os.makedirs(folder)
	response = requests.get(url)
	if response.status_code == 200:
		image_name = os.path.join(folder, os.path.basename(url))
		with open(image_name, 'wb') as f:
			f.write(response.content)
		return image_name
	return None

def scrape_post(url, date):
	soup = get_soup(url)
	title = soup.select_one('h1').get_text().strip() if soup.select_one('h1') else 'No Title'
	print(f"    Post title: {title}")
	post_date = date
	print(f"    Post date: {post_date}")
	author = "bjelakrez"  # Assuming the author is the same for all posts
	content_html = '\n'.join([str(p) for p in soup.select('div.entrycontent')])
	content = html2text.html2text(content_html)
	print(f"    Post content length: {len(content)} characters")
		
	# Download images and replace URLs in content
	image_urls = [img['src'] for img in soup.select('div.entrycontent img') if 'src' in img.attrs]
	for img_url in image_urls:
		full_img_url = urljoin(BASE_URL, img_url)  # Convert relative URL to absolute URL
		local_image_path = download_image(full_img_url, 'images')
		if local_image_path:
			content = content.replace(img_url, local_image_path)
		
	# Correctly find comments and authors
	comments = []
	for comment_div in soup.select('div.comment'):
		comment_text = html2text.html2text(str(comment_div.find('p')))
		author_tag = comment_div.find('p', class_='commentdetails').find('a')
		author_name = author_tag.get_text() if author_tag else 'Unknown'
			
		# Remove unnecessary line breaks
		comment_text = re.sub(r'\n+', '\n', comment_text).strip()
			
		# Download images in comments
		comment_images = comment_div.find_all('img')
		for img in comment_images:
			img_url = img['src']
			full_img_url = urljoin(BASE_URL, img_url)
			local_image_path = download_image(full_img_url, 'images')
			if local_image_path:
				comment_text = comment_text.replace(img_url, local_image_path)
			
		comments.append({'author': author_name, 'text': comment_text})

	print(f"    Number of comments: {len(comments)}\n")
		
	return {
		'title': title,
		'post_date': post_date,
		'author': author,
		'content': content,
		'comments': comments
	}

def clean_title(title):
	# Remove special characters and convert to lowercase
	return re.sub(r'[^a-zA-Z0-9\s]', '', title).replace(' ', '_').lower()

def save_post(post_data, filename):
	print(f"    Saving post: {post_data['title']} to {filename}")
	post = frontmatter.Post(post_data['content'])
	post['title'] = post_data['title']
	post['post_date'] = post_data['post_date']
	post['author'] = post_data['author']
	post['comments'] = post_data['comments']
    
	with open(filename, 'w', encoding='utf-8') as f:
		f.write(frontmatter.dumps(post))
	print(f"    Post saved: {filename}\n")

def main():
	posts = scrape_toc()
	if not os.path.exists('posts'):
		os.makedirs('posts')
	if not os.path.exists('posts/images'):
		os.makedirs('posts/images')
		
	for i, (title, url, date) in enumerate(posts):
		print(f"Scraping post {i+1}/{len(posts)}: {title}")
		post_data = scrape_post(url, date)
		clean_title_str = clean_title(title)
		date_str = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
		filename = f"posts/{date_str}_{clean_title_str}.md"
		save_post(post_data, filename)
		print(f"    Saved post to {filename}\n")

if __name__ == '__main__':
	main()