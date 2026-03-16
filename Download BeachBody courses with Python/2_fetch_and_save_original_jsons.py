def fetch_and_save_next_data():
	"""
	Reads each link from program_links.txt, fetches the page, locates 
	the __NEXT_DATA__ script, and saves it as a beautified JSON in 
	the "Original JSONs" folder. The filename is derived from the slug 
	in the URL after "/programs/". 
    
	For example, 
	'https://www.beachbodyondemand.com/programs/the-masters-hammer-and-chisel/start-here?locale=en_US'
	becomes "the-masters-hammer-and-chisel.json" in Original JSONs.
	"""
	import requests
	from bs4 import BeautifulSoup
	import json
	import os

	input_file = "program_links_all.txt"
	output_folder = "Original JSONs"
	next_data_id = "__NEXT_DATA__"

	# Make sure the output folder exists
	if not os.path.exists(output_folder):
		os.makedirs(output_folder)

	def extract_slug_from_url(url: str) -> str:
		"""
		Extract the portion after '/programs/' from the provided URL
		and strip query parameters and any trailing slash.
		"""
		if "/programs/" not in url:
			# Fallback if not found; just create a sanitized fallback
			# e.g. https://www.beachbodyondemand.com
			return url.replace("https://", "").replace("/", "_").split("?")[0]

		# Split off everything up to 'programs/' ...
		path_after_programs = url.split("/programs/")[1]
		# Remove anything after the first slash (if any), e.g. /start-here
		path_after_programs = path_after_programs.split("/")[0]
		# Remove query part
		path_after_programs = path_after_programs.split("?")[0]
		# Return as the slug
		return path_after_programs.strip()

	with open(input_file, "r", encoding="utf-8") as f:
		links = [line.strip() for line in f if line.strip()]

	for link in links:
		print(f"Fetching {link} ...")
		try:
			response = requests.get(link)
		except Exception as e:
			print(f"Error fetching {link}: {e}")
			continue

		if response.status_code != 200:
			print(f"Failed to fetch {link}, status code: {response.status_code}")
			continue

		soup = BeautifulSoup(response.text, "html.parser")
		next_data_script = soup.find("script", {"id": next_data_id, "type": "application/json"})
		if not next_data_script:
			print(f"Could not find __NEXT_DATA__ script for {link}")
			continue

		next_data_script_string = next_data_script.string
		if not next_data_script_string:
			print(f"__NEXT_DATA__ script is empty for {link}")
			continue

		# Parse the JSON from __NEXT_DATA__
		try:
			next_data = json.loads(next_data_script_string)
		except json.JSONDecodeError:
			print(f"JSON parse error for {link}")
			continue

		# Determine the filename based on URL slug
		slug = extract_slug_from_url(link)
		json_filename = os.path.join(output_folder, f"{slug}.json")

		# Write the beautified JSON
		with open(json_filename, "w", encoding="utf-8") as out_f:
			json.dump(next_data, out_f, indent=2)
		print(f"Saved beautified JSON to {json_filename}")

if __name__ == "__main__":
	fetch_and_save_next_data()