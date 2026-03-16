import re
import os
import sys

def extract_paths(file_path):
    # Determine the directory of the input file
    directory = os.path.dirname(file_path)
    
    # Output file paths
    single_dash_file = os.path.join(directory, 'single_dash_paths.txt')
    double_dash_file = os.path.join(directory, 'double_dash_paths.txt')

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Regular expressions to match lines starting with "    -/" or "    --/"
    single_dash_pattern = re.compile(r'^\s{4}-/(.+\.mp3)')
    double_dash_pattern = re.compile(r'^\s{4}--/(.+\.mp3)')

    single_dash_paths = []
    double_dash_paths = []

    # Process each line separately
    for line in lines:
        single_dash_match = single_dash_pattern.match(line)
        double_dash_match = double_dash_pattern.match(line)
        if single_dash_match:
            single_dash_paths.append('/' + single_dash_match.group(1))
        if double_dash_match:
            double_dash_paths.append('/' + double_dash_match.group(1))

    # Debug prints to verify extraction
    #print(f"Single dash paths: {single_dash_paths}")
    #print(f"Double dash paths: {double_dash_paths}")
    
    # Write single dash paths to the specified file
    with open(single_dash_file, 'w', encoding='utf-8') as file:
        for path in single_dash_paths:
            file.write(f'{path}\n')
    
    # Write double dash paths to the specified file
    with open(double_dash_file, 'w', encoding='utf-8') as file:
        for path in double_dash_paths:
            file.write(f'{path}\n')

    print(f"Paths with '-' have been written to {single_dash_file}")
    print(f"Paths with '--' have been written to {double_dash_file}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py path_to_your_text_file.txt")
        sys.exit(1)
    
    input_file_path = sys.argv[1]
    extract_paths(input_file_path)
