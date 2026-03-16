import os
import sys
import argparse

def find_lines_with_keywords(folder_path, keywords):
	# Check if the provided folder path exists and is a directory
	if not os.path.isdir(folder_path):
		print(f"Error: The path '{folder_path}' is not a valid directory.")
		sys.exit(1)
    
	# Iterate through all files in the directory
	for filename in os.listdir(folder_path):
		# Process only .txt files
		if filename.lower().endswith('.txt'):
			file_path = os.path.join(folder_path, filename)
			try:
				with open(file_path, 'r', encoding='utf-8') as file:
					for line in file:
						# Check if all keywords are present in the line (case-insensitive)
						if all(keyword.lower() in line.lower() for keyword in keywords):
							# Remove the file extension for output
							file_base = os.path.splitext(filename)[0]
							# Strip newline characters from the line
							clean_line = line.strip()
							print(f"{file_base}: {clean_line}")
							# If only the first matching line per file is needed, uncomment the next line
							# break
			except Exception as e:
				print(f"Error reading file '{filename}': {e}")

def main():
	parser = argparse.ArgumentParser(description="Search .txt files for lines containing specific keywords.")
	parser.add_argument('folder', type=str, help='Path to the folder containing .txt files')
	args = parser.parse_args()
    
	keywords = ["flow", "formerly"]
	find_lines_with_keywords(args.folder, keywords)

if __name__ == "__main__":
	main()
