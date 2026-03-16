import os
import shutil
import sys

def copy_files(file_list_path, target_directory):
    # Ensure the target directory exists
    print(f"Ensuring target directory exists: {target_directory}")
    os.makedirs(target_directory, exist_ok=True)

    with open(file_list_path, 'r') as file_list:
        print(f"Reading file list from: {file_list_path}")
        for file_path in file_list:
            file_path = file_path.strip()
            if os.path.isfile(file_path):
                print(f"Copying file: {file_path} to {target_directory}")
                shutil.copy(file_path, target_directory)
            else:
                print(f"File not found: {file_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py file_list.txt target_directory")
        sys.exit(1)

    file_list_path = sys.argv[1]
    target_directory = sys.argv[2]

    print(f"Starting copy process with file list: {file_list_path} and target directory: {target_directory}")
    copy_files(file_list_path, target_directory)
    print("Copy process completed.")