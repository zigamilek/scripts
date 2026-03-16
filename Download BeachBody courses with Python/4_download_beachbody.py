#!/usr/bin/env python3
"""
Script to parse a JSON of programs and download videos/files according to specified rules.

Usage:
	python download_assets.py --input-json /path/to/programs.json --output-folder /path/to/download

Requirements:
	- yt-dlp (for video downloads)
	- wget (for file downloads)
"""

import os
import re
import json
import argparse
import subprocess
from pathlib import Path

def sanitize_filename(name: str) -> str:
	"""
	Remove or replace characters that are unsafe for filenames.
	Specifically:
	- Replace ':' with ' -'
	- Remove '!'
	- Replace '.' with '_'
	- For other unsafe characters, replace with '_'.
	"""
	# Perform user-specified replacements first:
	name = name.replace(': ', ' - ')
	name = name.replace(' :', ' ')
	name = name.replace(':', ' ')
	name = name.replace('!', '')
	name = name.replace('.', '_')

	# Then replace remaining unsafe characters with underscore.
	name = re.sub(r'[/\\:*?"<>|]+', '_', name)

	return name

def get_extension_from_filename(filename: str) -> str:
	"""
	Extract file extension (including the leading dot) from a given filename (if it exists).
	Otherwise, return an empty string.
	"""
	# If there's a query param after '?', remove it first
	if '?' in filename:
		filename = filename.split('?')[0]
	_, ext = os.path.splitext(filename)
	return ext

def download_video(url: str, output_path: str):
	"""
	Download a video from the given url to the specified output_path using yt-dlp.
	Includes --concurrent-fragments 16 as specified.
	"""
	# Construct the directory part alone so it can be created
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
	# Use yt-dlp with concurrency
	# We also wrap the output template in quotes to allow for spaces.
	cmd = [
		"yt-dlp",
		#"--concurrent-fragments", "16",
		"--external-downloader", "aria2c",
		"-o", output_path,
		url
	]
	subprocess.run(cmd, check=True)

def download_file(url: str, output_path: str):
	"""
	Download a file from the given url to the specified output_path using wget.
	"""
	# Make sure the directory exists
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
	cmd = [
		"wget",
		"-O", output_path,
		url
	]
	subprocess.run(cmd, check=True)

def main():
	parser = argparse.ArgumentParser(description="Download videos/files from a JSON structure.")
	parser.add_argument("--input-json", required=True, help="Path to the input JSON file.")
	parser.add_argument("--output-folder", required=True, help="Path to the output folder.")
	args = parser.parse_args()

	input_json_path = args.input_json
	output_folder = args.output_folder

	# Load the JSON
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)

	# Prepare the already_downloaded file
	already_downloaded_path = os.path.join(output_folder, "already_downloaded.txt")
	already_downloaded = set()
	if os.path.exists(already_downloaded_path):
		with open(already_downloaded_path, "r", encoding="utf-8") as f:
			for line in f:
				line = line.strip()
				if line:
					already_downloaded.add(line)

	# Iterate over each program at the top-level of the JSON
	for program_key, program_data in data.items():
		# Make a folder name "trainer - title" from the data (or from the key).
		# The instructions say: "For each program, create a subfolder in the output folder, called 'trainer - title'."
		# The key itself might already look like "Chalene Johnson - PiYo".
		# But let's build it from the fields if possible, to match instructions exactly:
		trainer_name = program_data.get("trainer", "")
		program_title = program_data.get("title", "")
		# If either is missing, fallback to the program_key
		if trainer_name and program_title:
			program_folder_name = f"{trainer_name} - {program_title}"
		else:
			program_folder_name = program_key  # fallback
        
		program_folder_name = sanitize_filename(program_folder_name)
		program_folder_path = os.path.join(output_folder, program_folder_name)
		os.makedirs(program_folder_path, exist_ok=True)

		# --------------------------------
		# Download files (PDFs/other) to the program folder using wget
		# The JSON example has "files" => {someName => { ... "url": "...", "title": ... } }
		# We'll interpret that and download them as {title}.extension directly to program folder.
		files_obj = program_data.get("files", {})
		for _, file_info in files_obj.items():
			file_url = file_info.get("url")
			if not file_url:
				continue
            
			# Skip if already in already_downloaded
			if file_url in already_downloaded:
				print(f"Skipping already downloaded file: {file_url}")
				continue

			# Determine the file extension
			# The user wants the downloaded file to be "{title}.extension"
			file_title = file_info.get("title", "file")
			base_title = sanitize_filename(file_title)
            
			# Prefer the extension from the original_filename, else from the url
			orig_name = file_info.get("original_filename", "")
			extension = get_extension_from_filename(orig_name)
			if not extension:
				# fallback to url
				extension = get_extension_from_filename(file_url)
			if not extension:
				# fallback to .bin
				extension = ".bin"
            
			output_filename = f"{base_title}{extension}"
			output_file_path = os.path.join(program_folder_path, output_filename)
            
			print(f"Downloading file: {file_url} -> {output_file_path}")
			download_file(file_url, output_file_path)

			# Mark as downloaded
			with open(already_downloaded_path, "a", encoding="utf-8") as adf:
				adf.write(file_url + "\n")
			already_downloaded.add(file_url)

		# --------------------------------
		# Download videos
		# The JSON has "videos" => { sectionName => { moduleName => { videoName => videoData, ... }, ... }, ... }
		videos_obj = program_data.get("videos", {})

		# For each section in videos_obj
		for section_name, modules_obj in videos_obj.items():
			# "Start Here" special rule: "download all videos from the 'Start Here' section directly to the program folder as 'title.extension' (without numbering)."
			if section_name == "Start Here":
				# modules_obj is an object with multiple modules, each with multiple videos
				for module_name, videos_in_module in modules_obj.items():
					for vid_title, vid_info in videos_in_module.items():
						vid_url = vid_info.get("url")
						if not vid_url:
							continue
                        
						if vid_url in already_downloaded:
							print(f"Skipping already downloaded video: {vid_url}")
							continue

						# We'll guess extension from the url or just let yt-dlp handle it and store as .mp4
						safe_title = sanitize_filename(vid_info.get("title", "video"))
						# Using .mp4 as a default extension if m3u8 is present
						# We'll supply to yt-dlp an output pattern
						# For "Start Here" => store in program_folder, no numbering, just "title.extension"
                        
						# We'll set the extension to .mp4 or .mkv if we want. 
						# Let's default to .mp4, because we usually want an mp4.
						file_extension = ".mp4"
						out_filename = f"{safe_title}{file_extension}"
						out_full_path = os.path.join(program_folder_path, out_filename)

						print(f"Downloading video: {vid_url} -> {out_full_path}")
						download_video(vid_url, out_full_path)

						# Mark as downloaded
						with open(already_downloaded_path, "a", encoding="utf-8") as adf:
							adf.write(vid_url + "\n")
						already_downloaded.add(vid_url)

			else:
				# Other sections
				# Possibly multiple modules. If there's only one module, store them directly in a section folder (within the program folder).
				# If there's more than one module, store them in subfolders named after each module.
				# So let's see how many modules we have
				module_names = list(modules_obj.keys())
                
				# Create a subfolder for the section unless there's only one module and we will store them in that section folder
				safe_section_name = sanitize_filename(section_name)
				section_path = os.path.join(program_folder_path, safe_section_name)
                
				# If there's only one module, we store videos directly in the section folder (no sub-subfolder).
				# Otherwise, we store them in subfolders for each module.
				one_module = (len(module_names) == 1)
                
				for module_name, videos_in_module in modules_obj.items():
					# If there's only one module, store videos in section folder
					# Otherwise, create a subfolder for the module
					if one_module:
						module_path = section_path
					else:
						safe_module_name = sanitize_filename(module_name)
						module_path = os.path.join(section_path, safe_module_name)
                    
					# Now download each video in that module
					for vid_title, vid_info in videos_in_module.items():
						vid_url = vid_info.get("url")
						if not vid_url:
							continue

						if vid_url in already_downloaded:
							print(f"Skipping already downloaded video: {vid_url}")
							continue
                        
						video_number = vid_info.get("video_number")
						vid_safe_title = sanitize_filename(vid_info.get("title", "video"))
                        
						# Construct the output filename
						# If there's no "video_number", we can skip numbering. If present, we do: "{video_number:02d} - {title}.mp4"
						# The user specifically says: "Use yt-dlp with --concurrent-fragments 16 to download the videos as {section}/{module}/{video_number:02d} - {title}.extension."
						# We'll default extension to .mp4 again, unless user wants a different. We'll do mp4 for consistency.
						file_extension = ".mp4"
                        
						if video_number is not None:
							out_filename = f"{video_number:02d} - {vid_safe_title}{file_extension}"
						else:
							# fallback if no video_number
							out_filename = f"{vid_safe_title}{file_extension}"

						out_full_path = os.path.join(module_path, out_filename)
						print(f"Downloading video: {vid_url} -> {out_full_path}")
						download_video(vid_url, out_full_path)

						# Mark as downloaded
						with open(already_downloaded_path, "a", encoding="utf-8") as adf:
							adf.write(vid_url + "\n")
						already_downloaded.add(vid_url)

	print("All downloads completed successfully.")

if __name__ == "__main__":
	main()