import os
import re
import sys
from collections import defaultdict
from mutagen.mp3 import MP3

def extract_title(filename):
    """Extracts the title from the filename."""
    # Try to match the pattern with date and other information first
    match = re.search(r'(?:\d+ - \d{4}-\d{2}-\d{2} - )?(.+?) \(', filename)
    if match:
        return match.group(1)
    # If the first pattern does not match, try to get the title based on the filename itself
    # Remove file extension and any leading/trailing whitespace
    title = os.path.splitext(filename)[0].strip()
    # Replace underscores with spaces and return
    return title.replace('_', ' ')

def get_audio_length(file_path):
    """Returns the length of the audio in seconds."""
    try:
        audio = MP3(file_path)
        return int(audio.info.length)
    except Exception as e:
        print(f"Error getting length for {file_path}: {e}")
        return 0

def find_titles(folders, output_file):
    """Finds titles in the given folders and prints them."""
    # Dictionary to store titles and their corresponding file paths
    title_dict = defaultdict(list)
    
    # Process all folders
    for folder in folders:
        for root, _, files in os.walk(folder):
            # Only process the top-level directory
            if root != folder:
                continue
            for file in files:
                if file.endswith('.mp3'):
                    title = extract_title(file)
                    if title:
                        full_path = os.path.join(root, file)
                        file_size = os.path.getsize(full_path)
                        audio_length = get_audio_length(full_path)
                        # Use lowercase title for case-insensitive comparison
                        title_dict[title.lower()].append((title, full_path, audio_length, file_size))
    
    # Sort titles alphabetically
    sorted_titles = sorted(title_dict.keys())
    
    # Write the results to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        for counter, lower_title in enumerate(sorted_titles, 1):
            original_titles = list(set(t[0] for t in title_dict[lower_title]))
            # Display original titles for clarity
            f.write(f"{counter}. {' / '.join(original_titles)} - {len(title_dict[lower_title])} MP3s:\n")
            for _, path, length, size in title_dict[lower_title]:
                f.write(f"    {path} - {length} seconds - {size} bytes\n")
            f.write("\n")  # Empty line before next title

    # Finding duplicates ignoring case
    duplicates = {lower_title: paths for lower_title, paths in title_dict.items() if len(paths) > 1}
    
    # Write the duplicate results to another output file
    if duplicates:
        duplicates_output_file = os.path.join(os.path.dirname(output_file), 'duplicates.txt')
        with open(duplicates_output_file, 'w', encoding='utf-8') as f:
            for counter, lower_title in enumerate(sorted(duplicates.keys()), 1):
                original_titles = list(set(t[0] for t in duplicates[lower_title]))
                f.write(f"{counter}. {' / '.join(original_titles)} - {len(duplicates[lower_title])} MP3s:\n")
                for _, path, length, size in duplicates[lower_title]:
                    f.write(f"    {path} - {length} seconds - {size} bytes\n")
                f.write("\n")  # Empty line before next title
        print(f"Duplicate results have been saved to {duplicates_output_file}")
    else:
        print("No duplicates found.")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python find_titles.py <folder1> <folder2> [folder3]")
        sys.exit(1)

    folders = sys.argv[1:4]

    # Determine the path to the output file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'unique_titles.txt')

    find_titles(folders, output_file)
    print(f"Results have been saved to {output_file}")