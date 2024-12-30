import os
import shutil
import sys
import re
import tarfile
import zipfile

# Python Script for Linux, WSL or other Unix based systems 
# which runs through the given directory, or current working 
# directory if none is given, and organizes present files,
# grouping each by file name and version number if applicable,
# then creates and moves files into new directories. Any 
# unextracted files will be also extracted and organized before 
# deleting the originally downloaded .tar, .zip, .7z, etc.

def simplify_name(file_name):
    #Remove file extension
    base_name = os.path.splitext(file_name)[0]

    # Replace spaces with underscores
    base_name = base_name.replace(" ", "_")

    # Extract meaningful parts of the name (e.g., library, version, platform)
    match = re.match(r"([a-zA-Z0-9]+)[-_]?([0-9]+(\.[0-9]+)*)?[-_]?.*", base_name)
    if match:
        library = match.group(1)  # Main library name
        version = match.group(2) or ""  # Version number if present
        if version:
            return f"{library}-{version}"
        return library

    return base_name

def extract_file(file_path, extract_to):
    # Extract .tar, .tar.gz, .tar.bz2, .zip files
    try:
        if tarfile.is_tarfile(file_path):
            with tarfile.open(file_path) as tar:
                tar.extractall(path=extract_to)
                print(f"Extracted {file_path} to {extract_to}")
        elif zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
                print(f"Extracted {file_path} to {extract_to}")
        else:
            print(f"Unsupported archive format: {file_path}")
    except Exception as e:
        print(f"Failed to extract {file_path}: {e}")

def organize_downloads(base_dir):
    # Resolve the base directory
    if base_dir.startswith("$HOME"):
        base_dir = base_dir.replace("$HOME", os.path.expanduser("~"))

    if not os.path.exists(base_dir):
        print(f"The directory {base_dir} does not exist.")
        return

    # Iterate through the files and directories in the specified directory
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)

        # Skip directories
        if os.path.isdir(item_path):
            continue

        # Simplify the file name
        folder_name = simplify_name(item)

        # Extract the main group name (e.g., "SDL" from "SDL-3.1.6")
        group_match = re.match(r"([a-zA-Z]+)[-_]?.*", folder_name)
        group_name = group_match.group(1) if group_match else folder_name

        # Create the main group folder
        group_folder_path = os.path.join(base_dir, group_name)
        if not os.path.exists(group_folder_path):
            os.makedirs(group_folder_path)

        # Create the specific folder for the file
        specific_folder_path = os.path.join(group_folder_path, folder_name)
        if not os.path.exists(specific_folder_path):
            os.makedirs(specific_folder_path)

        # Extract the file if it's an archive
        if tarfile.is_tarfile(item_path) or zipfile.is_zipfile(item_path):
            extract_file(item_path, specific_folder_path)
            os.remove(item_path)  # Delete the archive after extraction
            print(f"Deleted {item_path} after extraction.")
        else:
            # Move the file into the specific folder
            new_file_path = os.path.join(specific_folder_path, item)
            shutil.move(item_path, new_file_path)
            print(f"Moved {item} to {specific_folder_path}")

if __name__ == "__main__":
    # Default to current directory if no arguments are provided
    base_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    organize_downloads(base_dir)
