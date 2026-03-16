def parse_programs():
	"""
	Reads JSON filenames from 'programs_to_download.txt' and loads the corresponding
	JSON from the 'Original JSONs' folder. Then builds a consolidated JSON whose
	top-level key is "trainer - title".
    
	For each program, it includes:
	  - title, description_short, program_id, subtitle, url, trainer,
		description_long, description_overview, commitment, duration,
		items, level, categories, equipment_required, equipment_recommended,
		classification, trainers, sections
	  - videos (organized by section → module → "XX - video_title"), 
		but ignoring modules or sections that have zero videos.
	  - files (keyed by file 'title', includes entity_id)
    
	Finally, saves the aggregated data to 'program_data.json'.
	"""
	import json
	import os
	from titlecase import titlecase

	# File that has a list of JSON filenames, e.g.:
	# barre-blend.json
	# beachbody-performance.json
	input_file = "programs_to_download.txt"
	output_file = "program_data.json"

	original_json_folder = "Original JSONs"
	if not os.path.exists(original_json_folder):
		os.makedirs(original_json_folder)

	final_data = {}

	def build_m3u8_url(video_id: str) -> str:
		"""
		Construct the m3u8 link:
		  https://d197pzlrcwv1zr.cloudfront.net/VIDEOID/VIDEOID_Main_B.m3u8
		"""
		return f"https://d197pzlrcwv1zr.cloudfront.net/{video_id}/{video_id}_Main_B.m3u8"

	def calculate_estimated_size_mb(duration_seconds: float) -> str:
		"""
		Estimate size using a 6000 kbit/s bitrate, then converting to MB.
		size_in_kbits = duration_seconds * 6000
		size_in_mb = size_in_kbits / 8.0 / 1024.0
		Returns a string like "786 MB".
		"""
		size_in_kbits = duration_seconds * 6000
		size_in_mb = size_in_kbits / 8.0 / 1024.0
		return f"{size_in_mb:.0f} MB"

	# Read JSON filenames from input_file
	with open(input_file, "r", encoding="utf-8") as file_in:
		program_json_files = [line.strip() for line in file_in if line.strip()]

	# For each JSON file, load that file from the Original JSONs folder
	for json_filename in program_json_files:
		print(f"Working on {json_filename}.")

		json_path = os.path.join(original_json_folder, json_filename)

		if not os.path.exists(json_path):
			print(f"File not found: {json_path}")
			continue

		# Load the raw data (equivalent to what next_data would have been)
		with open(json_path, "r", encoding="utf-8") as raw_file:
			try:
				next_data = json.load(raw_file)
			except json.JSONDecodeError:
				print(f"JSON parse error for {json_path}")
				continue

		# Usually the path is:
		# next_data["props"]["pageProps"]["reactQueryServerState"]["queries"][0]["state"]["data"]
		try:
			queries = next_data["props"]["pageProps"]["reactQueryServerState"]["queries"]
			top_data = queries[0]["state"]["data"]
		except (KeyError, IndexError):
			print(f"Could not parse the expected structure in {json_path}")
			continue

		entity_map = top_data.get("entities", {})

		program_id = top_data.get("_id", "")
		title = titlecase(top_data.get("title", ""))
		description_short = top_data.get("descriptionShort", "")
		subtitle = top_data.get("subtitle", "")

		# share.url
		share_data = top_data.get("share", {}) or {}
		url = share_data.get("url", "")

		# trainer name(s)
		trainers_array = top_data.get("trainers", [])
		if trainers_array:
			# Collect all trainer full names
			trainer_names = []
			for t in trainers_array:
				first_name = t.get("firstName", "").strip()
				last_name = t.get("lastName", "").strip()
				if first_name or last_name:
					trainer_names.append(f"{first_name} {last_name}".strip())
			# Join them with " & " or default to "Unknown Trainer"
			trainer_name = " & ".join(trainer_names) if trainer_names else "Unknown Trainer"
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

		# Prepare "videos" -> { section_title: { "XX - module_title": {"XX - vid_title": {...}} } }
		videos_by_section = {}
		# Prepare "files" -> keyed by file 'title'
		files_dict = {}

		for section_obj in sections:
			section_title = titlecase(section_obj.get("title", ""))
			modules = section_obj.get("modules", [])

			# We'll build a temporary dict of modules that actually have videos
			modules_dict_for_this_section = {}

			# Start counter for modules within this section
			module_counter = 1

			for mod_obj in modules:
				module_title = mod_obj.get("title", "") or ""
				module_title = titlecase(module_title)
				# Add a counter prefix to module_title
				module_title = f"{module_counter:02d} - {module_title}"

				entity_ids = mod_obj.get("entityIds", [])
				videos_dict_for_module = {}
				video_counter = 1

				for entity_id in entity_ids:
					entity_data = entity_map.get(entity_id, {})
					entity_type = entity_data.get("_type", "")

					if entity_type in ["workout", "promo"]:
						video_info = entity_data.get("video", {})
						video_id = video_info.get("videoId") or entity_data.get("videoId", "")
						if video_id:
							title_str = titlecase(entity_data.get("title", ""))
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

							# Key: "XX - video_title"
							video_key = f"{video_counter:02d} - {title_str}"

							videos_dict_for_module[video_key] = {
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
								"title": titlecase(entity_data.get("title", "")),
								"description": entity_data.get("description", ""),
								"original_filename": file_item.get("originalFilename", ""),
								"url": file_item.get("url", ""),
								"size": file_item.get("size", 0)
							}

				# Only add this module to the section if it has at least one video
				if videos_dict_for_module:
					modules_dict_for_this_section[module_title] = videos_dict_for_module

				# Increment module counter after each module
				module_counter += 1

			# Only add this section if it has at least one module with videos
			if modules_dict_for_this_section:
				videos_by_section[section_title] = modules_dict_for_this_section

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
			"videos": videos_by_section,  # Only includes sections and modules with videos
			"files": files_dict
		}

		# Compute the top-level key as "trainer - title"
		top_level_key = f"{trainer_name} - {title}".strip()
		final_data[top_level_key] = program_object

	# Finally, write out final_data to program_data.json
	with open(output_file, "w", encoding="utf-8") as f_out:
		json.dump(final_data, f_out, indent=2)
	print(f"Done! Wrote data to {output_file}")
    
if __name__ == "__main__":
	parse_programs()