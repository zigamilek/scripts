def parse_programs():
	"""
	Reads program links and creates a consolidated JSON whose top-level key is "trainer - title".
	For each program, it includes all the fields specified:
	  - title, description_short, program_id, subtitle, url, trainer, description_long,
		description_overview, commitment, duration, items, level, categories, equipment_required,
		equipment_recommended, classification, trainers, sections

	  - videos (now organized by section):
			{
			  "SectionTitle1": {
				  "module_title - 01 - video_title": {
					  "video_number": 1,
					  "video_id": "...",
					  ...
				  },
				  ...
			  },
			  "SectionTitle2": { ... }
			}

	  - files (stored as a dict keyed by the file 'title'):
			{
			  "Some File Title": {
				  "entity_id": "...",
				  "title": "Some File Title",
				  "description": "...",
				  "original_filename": "...",
				  "url": "...",
				  "size": 12345
			  },
			  ...
			}

	Also saves a beautified JSON of the raw NEXT_DATA in Original JSONs/TRAINER - TITLE.json.
	"""
	import requests
	from bs4 import BeautifulSoup
	import json
	import os

	input_file = "program_links.txt"
	output_file = "program_data.json"
	next_data_id = "__NEXT_DATA__"

	# Folder to store original NEXT_DATA JSONs
	original_json_folder = "Original JSONs"
	if not os.path.exists(original_json_folder):
		os.makedirs(original_json_folder)

	final_data = {}

	def build_m3u8_url(video_id: str) -> str:
		"""
		Construct the m3u8 link, e.g.:
		  https://d197pzlrcwv1zr.cloudfront.net/VIDEOID/VIDEOID_Main_B.m3u8
		"""
		return f"https://d197pzlrcwv1zr.cloudfront.net/{video_id}/{video_id}_Main_B.m3u8"

	def calculate_estimated_size_mb(duration_seconds: float) -> str:
		"""
		Estimate size using a 6000 kbit/s bitrate, then converting to MB.
		size_in_kbits = duration_seconds * 6000
		size_in_mb = size_in_kbits / 8 / 1024
		Returns a string, e.g. "786 MB".
		"""
		size_in_kbits = duration_seconds * 6000
		size_in_mb = size_in_kbits / 8.0 / 1024.0
		return f"{size_in_mb:.0f} MB"

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
			next_data = json.loads(next_data_script_string)
		except json.JSONDecodeError:
			print(f"JSON parse error for {link}")
			continue

		# Save raw data to beautified JSON
		raw_data_for_this_program = next_data

		# Usually the path is:
		# next_data["props"]["pageProps"]["reactQueryServerState"]["queries"][0]["state"]["data"]
		try:
			queries = next_data["props"]["pageProps"]["reactQueryServerState"]["queries"]
			top_data = queries[0]["state"]["data"]
		except (KeyError, IndexError):
			print(f"Couldn't navigate reactQueryServerState for {link}")
			continue

		entity_map = top_data.get("entities", {})

		program_id = top_data.get("_id", "")
		title = top_data.get("title", "")
		description_short = top_data.get("descriptionShort", "")
		subtitle = top_data.get("subtitle", "")

		# share.url
		share_data = top_data.get("share", {}) or {}
		url = share_data.get("url", "")

		# trainer name
		trainers_array = top_data.get("trainers", [])
		if trainers_array:
			first_name = trainers_array[0].get("firstName", "")
			last_name = trainers_array[0].get("lastName", "")
			trainer_name = f"{first_name} {last_name}".strip()
		else:
			trainer_name = "Unknown Trainer"

		description_long = top_data.get("descriptionLong", "")
		description_overview = top_data.get("descriptionOverview", "")

		# commitment.value + " " + commitment.title
		commitment_data = top_data.get("commitment", {}) or {}
		commitment_value = commitment_data.get("value", "")
		commitment_title = commitment_data.get("title", "")
		commitment_str = f"{commitment_value} {commitment_title}".strip()

		# duration.value + " " + duration.title
		duration_data = top_data.get("duration", {}) or {}
		duration_value = duration_data.get("value", "")
		duration_title = duration_data.get("title", "")
		duration_str = f"{duration_value} {duration_title}".strip()

		# items.value + " " + items.title
		items_data = top_data.get("itemCount", {}) or {}
		items_value = items_data.get("value", "")
		items_title = items_data.get("title", "")
		items_str = f"{items_value} {items_title}".strip()

		# level.title
		level_data = top_data.get("level", {}) or {}
		level_str = level_data.get("title", "")

		# arrays
		categories = top_data.get("categories", [])
		equipment_required = top_data.get("equipmentRequired", [])
		equipment_recommended = top_data.get("equipmentRecommended", [])
		classification = top_data.get("classification", [])
		trainers = top_data.get("trainers", [])
		sections = top_data.get("sections", [])

		# Prepare "videos" -> a dict of sections, each containing a dict of video_keys -> video data
		videos_by_section = {}
		# Prepare "files" -> keyed by resource's 'title'
		files_dict = {}

		# Go through sections and modules
		for section_obj in sections:
			section_title = section_obj.get("title", "")
			modules = section_obj.get("modules", [])

			# Ensure we have a dictionary entry for this section, even if no videos
			if section_title not in videos_by_section:
				videos_by_section[section_title] = {}

			for mod_obj in modules:
				module_title = mod_obj.get("title", "") or ""
				entity_ids = mod_obj.get("entityIds", [])

				# We'll track how many videos we find in this module
				video_counter = 1

				for entity_id in entity_ids:
					entity_data = entity_map.get(entity_id, {})
					entity_type = entity_data.get("_type", "")

					if entity_type in ["workout", "promo"]:
						video_info = entity_data.get("video", {})
						video_id = video_info.get("videoId") or entity_data.get("videoId", "")
						if video_id:
							# Basic data
							title_str = entity_data.get("title", "")
							video_trainers = entity_data.get("trainers", [])
							if video_trainers:
								vf_name = video_trainers[0].get("firstName", "")
								vl_name = video_trainers[0].get("lastName", "")
								video_trainer_name = f"{vf_name} {vl_name}".strip()
							else:
								video_trainer_name = ""

							levels_array = entity_data.get("levels", [])
							level_title = ""
							if levels_array:
								level_title = levels_array[0].get("title", "")

							duration_actual = video_info.get("durationActual", 0)
							estimated_size = calculate_estimated_size_mb(float(duration_actual))

							# Key: "module_title - XX - video_title"
							video_key = f"{module_title} - {video_counter:02d} - {title_str}"
							videos_by_section[section_title][video_key] = {
								"video_number": video_counter,
								"video_id": video_id,
								"title": title_str,
								"url": build_m3u8_url(video_id),
								"section": section_title,
								"module": module_title,
								"level": level_title,
								"trainer": video_trainer_name,
								"description": entity_data.get("descriptionLong", ""),
								"duration": duration_actual,
								"estimated_size": estimated_size,
								"focus_areas": entity_data.get("focusAreas", []),
								"categories": entity_data.get("categories", []),
								"subcategories": entity_data.get("subcategories", []),
								"levels": levels_array,
								"equipment_required": entity_data.get("equipmentRequired", []),
								"equipment_recommended": entity_data.get("equipmentRecommended", []),
								"trainers": video_trainers,
								"entity_id": entity_data.get("_id", entity_id),
							}
							video_counter += 1

					elif entity_type == "resource":
						file_item = entity_data.get("file")
						if file_item:
							file_title = entity_data.get("title", "Untitled File")
							files_dict[file_title] = {
								"entity_id": entity_data.get("_id", entity_id),
								"title": entity_data.get("title", ""),
								"description": entity_data.get("description", ""),
								"original_filename": file_item.get("originalFilename", ""),
								"url": file_item.get("url", ""),
								"size": file_item.get("size", 0)
							}
						else:
							continue

		# Build the final single object for this program
		program_object = {
			"title": title,
			"description_short": description_short,
			"program_id": program_id,
			"subtitle": subtitle,
			"url": url,
			"trainer": trainer_name,
			"description_long": description_long,
			"description_overview": description_overview,
			"commitment": commitment_str,
			"duration": duration_str,
			"items": items_str,
			"level": level_str,
			"categories": categories,
			"equipment_required": equipment_required,
			"equipment_recommended": equipment_recommended,
			"classification": classification,
			"trainers": trainers,
			"sections": sections,
			"videos": videos_by_section,  # Dict of {section_title: {video_key: {...}, ...}, ...}
			"files": files_dict          # Keyed by file title
		}

		# Compute the top-level key as "trainer - title"
		top_level_key = f"{trainer_name} - {title}".strip()

		final_data[top_level_key] = program_object

		# Save raw JSON in "Original JSONs/trainer - title.json"
		raw_json_path = os.path.join(original_json_folder, f"{top_level_key}.json")
		raw_json_path = raw_json_path.replace("/", "_")  # sanitize in case of slashes
		with open(raw_json_path, "w", encoding="utf-8") as raw_out:
			json.dump(raw_data_for_this_program, raw_out, indent=2)

	# Finally, write out final_data to program_data.json
	with open(output_file, "w", encoding="utf-8") as f_out:
		json.dump(final_data, f_out, indent=2)
	print(f"Done! Wrote data to {output_file}")


if __name__ == "__main__":
	parse_programs()