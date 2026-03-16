import os
import shutil
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import errno
import mimetypes

def make_soup(html_path):
	with open(html_path, 'r', encoding='utf-8') as file:
		return BeautifulSoup(file, 'html.parser')

def save_html(soup, output_path):
	with open(output_path, 'w', encoding='utf-8') as file:
		file.write(str(soup))

def create_directory(path):
	try:
		os.makedirs(path, exist_ok=True)
	except OSError as exc:
		if exc.errno != errno.EEXIST:
			raise

def get_extension(url, response=None):
	"""
	Determine the file extension from the URL or the response headers.
	"""
	parsed_url = urlparse(url)
	path = parsed_url.path
	ext = os.path.splitext(path)[1]
	if ext:
		return ext
	if response:
		content_type = response.headers.get('Content-Type')
		if content_type:
			return mimetypes.guess_extension(content_type.split(';')[0].strip()) or ''
	return ''

def download_asset(url, save_path):
	try:
		response = requests.get(url, stream=True)
		response.raise_for_status()
		# Determine the correct extension
		ext = get_extension(url, response)
		if not os.path.splitext(save_path)[1] and ext:
			save_path += ext
		with open(save_path, 'wb') as f:
			for chunk in response.iter_content(chunk_size=8192):
				f.write(chunk)
		print(f"Downloaded: {url} -> {save_path}")
		return os.path.basename(save_path)
	except Exception as e:
		print(f"Failed to download {url}: {e}")
		return None

def copy_asset(source_path, save_path):
	try:
		if not os.path.exists(source_path):
			print(f"Source asset does not exist: {source_path}")
			return None
		shutil.copy2(source_path, save_path)
		print(f"Copied: {source_path} -> {save_path}")
		return os.path.basename(save_path)
	except Exception as e:
		print(f"Failed to copy {source_path}: {e}")
		return None

def process_asset(asset_tag, asset_attr, asset_url, assets_dir):
	"""
	Process an individual asset by downloading or copying it locally.
	Returns the local filename if successful, else None.
	"""
	parsed_url = urlparse(asset_url)
	if parsed_url.scheme in ['http', 'https']:
		# Remote asset
		filename = os.path.basename(parsed_url.path)
		if not filename:
			# Handle URLs without a basename
			filename = 'asset'
		local_asset_path = os.path.join(assets_dir, filename)
		# Download the asset and handle extensions
		downloaded_filename = download_asset(asset_url, local_asset_path)
		if downloaded_filename:
			return downloaded_filename
	elif parsed_url.scheme == '' and not asset_url.startswith('//'):
		# Relative or absolute local path
		asset_path = os.path.join(dir_path, asset_url)
		if os.path.exists(asset_path):
			filename = os.path.basename(asset_path)
			local_asset_path = os.path.join(assets_dir, filename)
			copied_filename = copy_asset(asset_path, local_asset_path)
			if copied_filename:
				return copied_filename
		else:
			print(f"Local asset not found: {asset_path}")
	else:
		# Handle protocol-relative URLs or other schemes if necessary
		print(f"Skipping unsupported asset URL: {asset_url}")
	return None

def process_html_file(html_path):
	print(f"\nProcessing HTML file: {html_path}")
	soup = make_soup(html_path)
	dir_path = os.path.dirname(html_path)
	base_filename = os.path.splitext(os.path.basename(html_path))[0]
	assets_dir = os.path.join(dir_path, f"{base_filename}-files")
	create_directory(assets_dir)

	# Define tags and their attributes that hold asset URLs
	asset_tags = {
		'img': ['src', 'data-imageloader-src', 'data-src'],
		'script': ['src'],
		'link': ['href'],
		'video': ['src'],
		'source': ['src'],
		# Add more tags and attributes if needed
	}

	for tag, attrs in asset_tags.items():
		for asset in soup.find_all(tag):
			for attr in attrs:
				asset_url = asset.get(attr)
				if not asset_url:
					continue
				# Avoid processing the same asset multiple times
				# You can implement caching here if needed

				# Process the asset
				local_filename = process_asset(tag, attr, asset_url, assets_dir)
				if local_filename:
					# Update the asset reference to the local path
					relative_path = os.path.join(f"{base_filename}-files", local_filename)
					asset[attr] = relative_path.replace('\\', '/')  # Use forward slashes for URLs

	# Save the modified HTML
	local_html_path = os.path.join(dir_path, f"{base_filename}-local.html")
	save_html(soup, local_html_path)
	print(f"Saved localized HTML: {local_html_path}")

def traverse_and_process(root_dir):
	for dirpath, dirnames, filenames in os.walk(root_dir):
		global dir_path
		dir_path = dirpath  # Needed for relative asset paths
		for filename in filenames:
			if filename.lower().endswith('.html'):
				html_path = os.path.join(dirpath, filename)
				process_html_file(html_path)

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(description="Localize HTML files and their assets.")
	parser.add_argument('root_directory', help='Root directory to start processing')
	args = parser.parse_args()

	if not os.path.isdir(args.root_directory):
		print(f"Error: The directory '{args.root_directory}' does not exist.")
		exit(1)

	traverse_and_process(args.root_directory)
