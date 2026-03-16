from bs4 import BeautifulSoup

# Step 1: Read HTML from a file
input_file = 'input.html'  # Replace with your HTML file path if different

try:
	with open(input_file, 'r', encoding='utf-8') as file:
		html_content = file.read()
except FileNotFoundError:
	print(f"Error: The file '{input_file}' does not exist.")
	exit(1)

# Step 2: Parse the HTML content using BeautifulSoup
soup = BeautifulSoup(html_content, 'lxml')  # Use 'html.parser' if 'lxml' is not installed

# Step 3: Find all <video> tags and extract their 'id' attributes
video_tags = soup.find_all('video')
video_ids = [video.get('id') for video in video_tags if video.get('id')]

if not video_ids:
	print("No <video> tags with 'id' attributes found in the HTML.")
	exit(0)

# Step 4: Clean the video IDs by removing the 'video-' prefix
clean_video_ids = [vid.replace('video-', '') for vid in video_ids]

# Step 5: Create class links using the cleaned video IDs
base_url = "https://ondemand.animalflow.com/classes/"
class_links = [f"{base_url}{vid}" for vid in clean_video_ids]

# Step 6: Save the class links to 'class_links.txt'
output_file = 'class_links.txt'
try:
	with open(output_file, 'w', encoding='utf-8') as outfile:
		for link in class_links:
			outfile.write(f"{link}\n")
	print(f"Successfully extracted {len(class_links)} class link(s) and saved to '{output_file}'.")
except Exception as e:
	print(f"Error writing to file '{output_file}': {e}")
	exit(1)
