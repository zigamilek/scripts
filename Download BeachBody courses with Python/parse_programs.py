def parse_programs():
	"""
	Reads program links and creates a consolidated JSON with all the information needed
	(program_name, trainer, sections, videos, files, etc.) from the NEXT_DATA script on each page.
	"""
	import requests
	from bs4 import BeautifulSoup
	import json
	import re
	import os

	input_file = "program_links.txt"
	output_file = "program_data.json"

	# The script ID or marker used to find the __NEXT_DATA__ JSON
	next_data_id = "__NEXT_DATA__"

	all_programs_data = []

	# Helper: build m3u8 link from video_id
	def build_m3u8_url(video_id: str) -> str:
		# Example pattern: https://d197pzlrcwv1zr.cloudfront.net/BBR0037/BBR0037_Main_B.m3u8
		return f"https://d197pzlrcwv1zr.cloudfront.net/{video_id}/{video_id}_Main_B.m3u8"

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

		# Parse the JSON data
		try:
			json_data = json.loads(next_data_script_string)
		except json.JSONDecodeError:
			print(f"JSON parse error for {link}")
			continue

		# Navigate to the path "props.pageProps" in the JSON
		page_props = json_data.get("props", {}).get("pageProps", {})
		program_data = page_props.get("slug")  # Sometimes "slug" is program slug
		# The actual program metadata seems to be in "reactQueryServerState.queries[0].state.data"
		# We'll try to find that data:
		queries = page_props.get("reactQueryServerState", {}).get("queries", [])
		# Typically, the "data" is somewhere in queries->state->data, we find the one that references the program slug
		relevant_data = None
		for query_entry in queries:
			state_data = query_entry.get("state", {}).get("data")
			if state_data and isinstance(state_data, dict):
				# If it has something like "_type": "program" or "slug": "barre-blend"
				if state_data.get("_type") == "program" or state_data.get("slug") == page_props.get("slug"):
					relevant_data = state_data
					break

		if not relevant_data:
			print(f"Could not find relevant program data in JSON for {link}")
			continue

		program_title = relevant_data.get("title", "Unknown Title")
		trainers_data = relevant_data.get("trainers", [])
		trainer_name = ""
		if trainers_data:
			first_name = trainers_data[0].get("firstName", "").strip()
			last_name = trainers_data[0].get("lastName", "").strip()
			trainer_name = f"{first_name} {last_name}"

		# Grab about/stats/etc. (like you mentioned: everything for an "about" txt). 
		# They might be in "statistics" or "commitment" or "duration" or "descriptionShort/Long"
		# We'll bucket them into an "about" dict
		about_data = {
			"description_short": relevant_data.get("descriptionShort", ""),
			"description_long": relevant_data.get("descriptionLong", ""),
			"commitment": relevant_data.get("commitment", {}),
			"duration": relevant_data.get("duration", {}),
			"item_count": relevant_data.get("itemCount", {}),
			"level": relevant_data.get("level", {}),
			"statistics": [],
		}

		# Sometimes there's a "sections" or "modules" array with stats:
		# Or a "statistics" array within the dynamicModule
		# We'll see if there's a top-level "statistics" in relevant_data (as sometimes seen)
		top_level_stats = relevant_data.get("statistics", [])
		for stat in top_level_stats:
			about_data["statistics"].append(stat)

		# We'll also gather "sections" and "videos" from the "sections" array
		sections_data = relevant_data.get("sections", [])
		sections_list = []
		videos_list = []
		files_list = []

		# We'll need a map of entity_id -> entity details, which is in "page_props['reactQueryServerState']['queries'][0]['state']['data']" as well
		# Looking for keys like "A3jSdym3jf5hqTWanxQofJ":{"_id":"A3jSdym3jf5hqTWanxQofJ","_type":"workout", ...}
		# Often stored in relevant_data["entities"] or similar
		# In the sample, these are just nested under relevant_data itself (like "STf6JLOAKHfcDUeIJbo8F1" : { ... })
		# So let's look for all top-level keys that are dict and have "_type" in them
		entity_map = {}
		for key, val in relevant_data.items():
			if isinstance(val, dict) and "_type" in val:
				entity_map[key] = val

		# Extract each section
		for section in sections_data:
			section_title = section.get("title", "")
			section_slug = section.get("slug", "")
			section_dict = {
				"section_title": section_title,
				"slug": section_slug
			}
			sections_list.append(section_dict)

			# Each section might contain a "modules" or "entityIds" array. 
			# If it's a collection, we can iterate entityIds
			modules = section.get("modules", [])
			for module_item in modules:
				if module_item.get("_type") == "collection":
					entity_ids = module_item.get("entityIds", [])
					for entity_id in entity_ids:
						entity_data = entity_map.get(entity_id, {})
						entity_type = entity_data.get("_type", "")
						# If it's a "promo" or "workout", maybe it's a video
						if entity_type in ["promo", "workout"]:
							video_id = entity_data.get("video", {}).get("videoId")
							if not video_id:
								video_id = entity_data.get("videoId")  # fallback
							if video_id:
								new_video = {
									"section_title": section_title,
									"title": entity_data.get("title", ""),
									"description": entity_data.get("descriptionLong", ""),
									"video_id": video_id,
									"m3u8_url": build_m3u8_url(video_id)
								}
								videos_list.append(new_video)

						elif entity_type in ["resource"]:
							file_data = entity_data.get("file")
							if file_data:
								new_file = {
									"section_title": section_title,
									"title": entity_data.get("title", ""),
									"url": file_data.get("url", ""),
									"size": file_data.get("size", 0),
									"extension": file_data.get("extension", ""),
								}
								files_list.append(new_file)

		# Some sections have "entityIds" at the top-level (like in the provided example)
		for section in sections_data:
			entity_ids = section.get("entityIds", [])
			for entity_id in entity_ids:
				entity_data = entity_map.get(entity_id, {})
				entity_type = entity_data.get("_type", "")
				if entity_type in ["promo", "workout"]:
					video_id = entity_data.get("video", {}).get("videoId")
					if not video_id:
						video_id = entity_data.get("videoId")
					if video_id:
						new_video = {
							"section_title": section.get("title", ""),
							"title": entity_data.get("title", ""),
							"description": entity_data.get("descriptionLong", ""),
							"video_id": video_id,
							"m3u8_url": build_m3u8_url(video_id)
						}
						videos_list.append(new_video)
				elif entity_type in ["resource"]:
					file_data = entity_data.get("file")
					if file_data:
						new_file = {
							"section_title": section.get("title", ""),
							"title": entity_data.get("title", ""),
							"url": file_data.get("url", ""),
							"size": file_data.get("size", 0),
							"extension": file_data.get("extension", ""),
						}
						files_list.append(new_file)

		program_dict = {
			"program_name": program_title,
			"url": link,
			"trainer": trainer_name.strip(),
			"about": about_data,
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