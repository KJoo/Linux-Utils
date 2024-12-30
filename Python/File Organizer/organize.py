import os
import shutil
import sys
import re
import tarfile
import zipfile
import logging
import concurrent.futures
import py7zr  # For .7z support

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Python Script for Linux, WSL or other Unix-based systems
# This script organizes files by grouping them based on their names and version numbers,
# extracting archives when needed, and allowing for concurrent processing. Logs can be
# made verbose with a -v or --verbose flag.

def simplify_name(file_name):
    # Remove file extension
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
    # Extract .tar, .tar.gz, .tar.bz2, .zip, and .7z files
    try:
        if tarfile.is_tarfile(file_path):
            with tarfile.open(file_path) as tar:
                tar.extractall(path=extract_to)
                logging.info(f"Extracted {file_path} to {extract_to}")
        elif zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
                logging.info(f"Extracted {file_path} to {extract_to}")
        elif file_path.endswith(".7z"):
            with py7zr.SevenZipFile(file_path, 'r') as archive:
                archive.extractall(path=extract_to)
                logging.info(f"Extracted {file_path} to {extract_to}")
        else:
            logging.warning(f"Unsupported archive format: {file_path}")
    except Exception as e:
        logging.error(f"Failed to extract {file_path}: {e}")

def process_file(item, base_dir):
    item_path = item.path

    # Simplify the file name
    folder_name = simplify_name(item.name)

    # Extract the main group name (e.g., "SDL" from "SDL-3.1.6")
    group_match = re.match(r"([a-zA-Z]+)[-_]?.*", folder_name)
    group_name = group_match.group(1) if group_match else folder_name

    # Create the main group folder
    group_folder_path = os.path.join(base_dir, group_name)
    os.makedirs(group_folder_path, exist_ok=True)

    # Create the specific folder for the file
    specific_folder_path = os.path.join(group_folder_path, folder_name)
    os.makedirs(specific_folder_path, exist_ok=True)

    # Extract the file if it's an archive
    if tarfile.is_tarfile(item_path) or zipfile.is_zipfile(item_path) or item_path.endswith(".7z"):
        extract_file(item_path, specific_folder_path)
        os.remove(item_path)  # Delete the archive after extraction
        logging.info(f"Deleted {item_path} after extraction.")
    else:
        # Move the file into the specific folder
        new_file_path = os.path.join(specific_folder_path, item.name)
        shutil.move(item_path, new_file_path)
        logging.info(f"Moved {item.name} to {specific_folder_path}")

def organize_downloads(base_dir, verbosity=False):
    # Adjust logging level based on verbosity
    if verbosity:
        logging.getLogger().setLevel(logging.INFO)

    # Resolve the base directory
    if base_dir.startswith("$HOME"):
        base_dir = base_dir.replace("$HOME", os.path.expanduser("~"))

    if not os.path.exists(base_dir):
        logging.error(f"The directory {base_dir} does not exist.")
        return

    # Iterate through the files and directories in the specified directory concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_file, item, base_dir) for item in os.scandir(base_dir) if not item.is_dir()]
        for future in concurrent.futures.as_completed(futures):
            future.result()  # Ensure any exceptions are raised

if __name__ == "__main__":
    # Parse command-line arguments
    args = sys.argv[1:]
    verbosity = "-v" in args or "--verbose" in args

    # Get the base directory
    base_dir = next((arg for arg in args if not arg.startswith("-")), os.getcwd())

    organize_downloads(base_dir, verbosity)
