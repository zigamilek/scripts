def parse_programs():
	"""
	Reads program links and creates a consolidated JSON with all the information needed
	(program_name, trainer, sections, videos, files, etc.) from the NEXT_DATA script on each page.
	"""
	import requests
	from bs4 import BeautifulSoup
	import json
	import os

	input_file = "program_links.txt"
	output_file = "program_data.json"
	next_data_id = "__NEXT_DATA__"

	all_programs_data = []

	def build_m3u8_url(video_id: str) -> str:
		"""
		Example pattern for constructing the m3u8 link:
		https://d197pzlrcwv1zr.cloudfront.net/BBR0037/BBR0037_Main_B.m3u8
		"""
		return f"https://d197pzlrcwv1zr.cloudfront.net/{video_id}/{video_id}_Main_B.m3u8"

	# Read the program links from a file
	with open(input_file, "r", encoding="utf-8") as file_in:
		program_links = [line.strip() for line in file_in if line.strip()]

	for link in program_links:
		print(f"Fetching {link} ...")
		response = requests.get(link)
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
			json_data = json.loads(next_data_script_string)
		except json.JSONDecodeError:
			print(f"JSON parse error for {link}")
			continue

		# Typical path to reach the top-level object containing the program data:
		# json_data["props"]["pageProps"]["reactQueryServerState"]["queries"][0]["state"]["data"]
		# Adjust as necessary if your data is nested differently.
		try:
			queries = json_data["props"]["pageProps"]["reactQueryServerState"]["queries"]
			top_data = queries[0]["state"]["data"]  # You might need to search for the correct index
		except (KeyError, IndexError):
			print(f"Couldn't navigate reactQueryServerState for {link}")
			continue

		# “entities” often contains a dict of _id -> {metadata}, e.g. videos, resources, etc.
		entity_map = top_data.get("entities", {})

		# Basic program info
		program_title = top_data.get("title", "")
		slug = top_data.get("slug", "")
		trainer_data = top_data.get("trainers", [])

		# Example: get first trainer's first+last name if available
		if trainer_data:
			first_name = trainer_data[0].get("firstName", "")
			last_name = trainer_data[0].get("lastName", "")
			trainer_name = f"{first_name} {last_name}"
		else:
			trainer_name = ""

		# “about” data could come from multiple places (statistics, descriptionLong, etc.)
		# As an example, gather some “statistics” from the first module in the first section
		about_data = {}
		sections_data = top_data.get("sections", [])

		# We'll collect these for the entire program
		sections_list = []
		videos_list = []
		files_list = []

		# Let's store the sections in a simpler format
		for section in sections_data:
			section_title = section.get("title", "")
			# You can also store "slug" or other relevant fields
			sections_list.append({"title": section_title})

		#
		# Now parse out videos/resources by iterating modules → entityIds → entity_map
		#
		for section in sections_data:
			section_title = section.get("title", "")
			modules = section.get("modules", [])
			for module_obj in modules:
				entity_ids = module_obj.get("entityIds", [])
				for entity_id in entity_ids:
					entity_data = entity_map.get(entity_id, {})
					entity_type = entity_data.get("_type", "")

					# Videos often have _type in ["promo", "workout"]
					if entity_type in ["promo", "workout"]:
						# Sometimes the videoId is in entity_data["video"]["videoId"]
						video_id = entity_data.get("video", {}).get("videoId")
						# Or directly at entity_data["videoId"]
						if not video_id:
							video_id = entity_data.get("videoId")

						if video_id:
							video_title = entity_data.get("title", "")
							video_description = entity_data.get("descriptionLong", "")
							videos_list.append({
								"section_title": section_title,
								"title": video_title,
								"description": video_description,
								"video_id": video_id,
								"m3u8_url": build_m3u8_url(video_id),
							})

					# Files often have _type == "resource", with a "file" child
					elif entity_type == "resource":
						file_data = entity_data.get("file")
						if file_data:
							files_list.append({
								"section_title": section_title,
								"title": entity_data.get("title", ""),
								"url": file_data.get("url"),
								"size": file_data.get("size", 0),
								"extension": file_data.get("extension", ""),
							})

		# Build the final program dictionary
		program_dict = {
			"program_name": program_title,
			"url": link,
			"trainer": trainer_name.strip(),
			"about": about_data,   # You can populate with anything else you want
			"sections": sections_list,
			"videos": videos_list,
			"files": files_list
		}

		all_programs_data.append(program_dict)

	# Write out a single JSON file containing all programs
	with open(output_file, "w", encoding="utf-8") as file_out:
		json.dump({"programs": all_programs_data}, file_out, indent=2)

	print(f"Done! Wrote data to {output_file}")


if __name__ == "__main__":
	parse_programs()