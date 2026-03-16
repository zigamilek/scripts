#!/usr/bin/env python3

import os
import json
import argparse
import subprocess
import sys
import re

def sanitize_filename(name):
    """
    Sanitize the filename by removing the '#' character and any other characters
    that are invalid in file names.
    """
    # Remove '#' characters
    name = name.replace('#', '')
    # Remove any character that is not alphanumeric, space, dot, underscore, or hyphen
    name = re.sub(r'[^\w\s.-]', '', name)
    # Replace spaces with underscores
    name = re.sub(r'\s+', '_', name)
    return name

def load_json(json_path):
    """
    Load the JSON data from the given path.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

def download_video(url, output_path, cookies_path):
    """
    Use yt-dlp to download the video from the given URL to the specified output path.
    Returns True if download was successful, False otherwise.
    """
    command = [
        'yt-dlp',
        url,
        '--cookies', cookies_path,
        '--external-downloader', 'aria2c',
        '-o', output_path
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Downloaded: {url}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download {url}: {e}")
        return False

def load_already_downloaded(file_path):
    """
    Load the already downloaded URLs from the given file into a set.
    If the file doesn't exist, create it and return an empty set.
    """
    if not os.path.exists(file_path):
        # Create the file if it doesn't exist
        with open(file_path, 'w', encoding='utf-8') as f:
            pass
        return set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            downloaded = set(line.strip() for line in f if line.strip())
        return downloaded
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        sys.exit(1)

def append_to_already_downloaded(file_path, url):
    """
    Append a successfully downloaded URL to the already_downloaded file.
    """
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(url + '\n')
    except Exception as e:
        print(f"Error writing to {file_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Download videos using yt-dlp based on a JSON file.")
    parser.add_argument('--output-folder', required=True, help='Path to the output folder where videos will be saved.')
    parser.add_argument('--json-file', default='programs_data.json', help='Path to the JSON file containing video URLs. Default is programs_data.json')
    args = parser.parse_args()

    output_folder = args.output_folder
    json_file = args.json_file

    # Ensure output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Path to cookies.txt
    cookies_path = os.path.join(script_dir, 'cookies.txt')
    if not os.path.exists(cookies_path):
        print(f"cookies.txt not found in {script_dir}")
        sys.exit(1)

    # Path to already_downloaded.txt
    already_downloaded_path = os.path.join(script_dir, 'already_downloaded.txt')
    
    # Load already downloaded URLs
    already_downloaded = load_already_downloaded(already_downloaded_path)
    print(f"Loaded {len(already_downloaded)} already downloaded URLs.")

    # Load JSON data
    data = load_json(json_file)

    for program_name, program_info in data.items():
        sanitized_program_name = sanitize_filename(program_name)
        program_folder = os.path.join(output_folder, sanitized_program_name)

        # Create program folder if it doesn't exist
        os.makedirs(program_folder, exist_ok=True)

        workouts = program_info.get('workouts', {})
        for workout_name, workout_info in workouts.items():
            url = workout_info.get('url')
            if not url:
                print(f"No URL found for workout: {workout_name}")
                continue

            if url in already_downloaded:
                print(f"Skipping already downloaded URL: {url}")
                continue

            sanitized_workout_name = sanitize_filename(workout_name)
            # Define the output template
            output_template = os.path.join(program_folder, f"{sanitized_workout_name}.%(ext)s")

            print(f"Starting download for: {sanitized_workout_name}")
            success = download_video(url, output_template, cookies_path)
            if success:
                append_to_already_downloaded(already_downloaded_path, url)
                already_downloaded.add(url)  # Update the set to include the newly downloaded URL

if __name__ == "__main__":
    main()
