import os
import shutil
import sys
import re
import tarfile
import zipfile
import logging
import concurrent.futures
import py7zr  # For .7z support
import rarfile  # For .rar support
import gzip  # For .gz support
from tqdm import tqdm  # For progress bar

# Configure logging with support for dynamic configuration via arguments or environment variables
def configure_logging():
    log_level = os.getenv("LOG_LEVEL", "WARNING").upper()
    log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")
    logging.basicConfig(level=getattr(logging, log_level, logging.WARNING), format=log_format)

configure_logging()

# Check RAR support globally
RAR_SUPPORTED = rarfile.is_rarfile_supported()
if not RAR_SUPPORTED:
    logging.warning("RAR support requires 'unrar' or 'bsdtar' installed on your system.")

"""
Script: organize.py

Description:
This script takes a directory and organizes files found within by grouping them based on their names and version numbers. 
It supports extracting a variety of archive formats, processes files concurrently for better performance, and offers 
a simulation mode to preview changes before making them. Suitable for Linux, WSL, and other Unix-like systems.

Features:
- Supports multiple archive formats: .tar, .zip, .7z, .rar, .gz
- Groups files into directories based on simplified names and versioning.
- Allows concurrent processing with customizable thread limits.
- Simulation mode for previewing changes.
- Verbosity control for detailed logging.
- Help documentation for usage instructions.

Usage:
  python organize.py [directory] [options]

Options:
  -v, --verbose          Enable detailed logging.
  -s, --simulate         Simulate changes without modifying files.
  -t N, --threads=N      Limit the number of threads for concurrent processing.
  -h, --help             Display help documentation.

Example:
  python organize.py ~/Downloads -v --simulate --threads=8
"""

def simplify_name(file_name):
    """
    Simplify the given file name by removing extensions and replacing spaces with underscores.

    Args:
        file_name (str): The name of the file to simplify.

    Returns:
        str: The simplified file name.
    """
    base_name = os.path.splitext(file_name)[0]
    base_name = base_name.replace(" ", "_")
    name_pattern = re.compile(r"([a-zA-Z0-9]+)[-_]?([0-9]+(?:\.[0-9]+)*)?[-_]?.*")
    match = name_pattern.match(base_name)
    if match:
        library = match.group(1)
        version = match.group(2) or ""
        return f"{library}-{version}" if version else library
    return base_name


def extract_file(file_path, extract_to, simulation):
    """
    Extract the given archive file to the specified directory.

    Args:
        file_path (str): The path to the archive file.
        extract_to (str): The directory to extract the contents to.
        simulation (bool): If True, simulate extraction without making changes.

    Raises:
        Exception: If the extraction process fails.
    """
    try:
        if tarfile.is_tarfile(file_path):
            if not simulation:
                with tarfile.open(file_path) as tar:
                    tar.extractall(path=extract_to)
            logging.info(f"Extracted {file_path} to {extract_to}")
        elif zipfile.is_zipfile(file_path):
            if not simulation:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            logging.info(f"Extracted {file_path} to {extract_to}")
        elif file_path.endswith(".7z"):
            if not simulation:
                with py7zr.SevenZipFile(file_path, 'r') as archive:
                    archive.extractall(path=extract_to)
            logging.info(f"Extracted {file_path} to {extract_to}")
        elif file_path.endswith(".rar"):
            if not RAR_SUPPORTED:
                return False
            if not simulation:
                with rarfile.RarFile(file_path) as rar:
                    rar.extractall(path=extract_to)
            logging.info(f"Extracted {file_path} to {extract_to}")
        elif file_path.endswith(".gz"):
            if not simulation:
                with gzip.open(file_path, 'rb') as f_in:
                    with open(os.path.join(extract_to, os.path.basename(file_path).replace('.gz', '')), 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            logging.info(f"Extracted {file_path} to {extract_to}")
        else:
            logging.warning(f"Unsupported archive format: {file_path}")
            return False
        return True
    except Exception as e:
        logging.error(f"Failed to extract {file_path}: {e}")
        return False


def process_file(item, base_dir, simulation):
    """
    Process a single file by simplifying its name, extracting if necessary, and moving it to the appropriate directory.

    Args:
        item (os.DirEntry): The file to process.
        base_dir (str): The base directory to organize files into.
        simulation (bool): If True, simulate processing without making changes.
    """
    item_path = item.path
    folder_name = simplify_name(item.name)
    group_match = re.match(r"([a-zA-Z]+)[-_]?.*", folder_name)
    group_name = group_match.group(1) if group_match else folder_name
    group_folder_path = os.path.join(base_dir, group_name)
    specific_folder_path = os.path.join(group_folder_path, folder_name)

    if not simulation:
        os.makedirs(group_folder_path, exist_ok=True)
        os.makedirs(specific_folder_path, exist_ok=True)

    if tarfile.is_tarfile(item_path) or zipfile.is_zipfile(item_path) or item_path.endswith((".7z", ".rar", ".gz")):
        success = extract_file(item_path, specific_folder_path, simulation)
        if success and not simulation:
            os.remove(item_path)
            logging.info(f"Deleted {item_path} after extraction.")
        elif not success:
            logging.warning(f"Fallback: Moving {item_path} to {specific_folder_path} without extraction.")
            if not simulation:
                shutil.move(item_path, specific_folder_path)
    else:
        new_file_path = os.path.join(specific_folder_path, item.name)
        if not simulation:
            shutil.move(item_path, new_file_path)
        logging.info(f"Moved {item.name} to {specific_folder_path}")


def organize_downloads(base_dir, verbosity=False, simulation=False, max_threads=4):
    """
    Organize files in the specified base directory by grouping them based on their names and version numbers.

    Args:
        base_dir (str): The base directory to organize files into.
        verbosity (bool): Enable verbose logging if True.
        simulation (bool): If True, simulate organization without making changes.
        max_threads (int): Limit the number of threads for concurrent processing.
    """
    if verbosity:
        logging.getLogger().setLevel(logging.INFO)
    if base_dir.startswith("$HOME"):
        base_dir = base_dir.replace("$HOME", os.path.expanduser("~"))
        if not os.path.isdir(base_dir):
            logging.error(f"Resolved path is not a valid directory: {base_dir}")
            return

    if not os.path.exists(base_dir):
        logging.error(f"The directory {base_dir} does not exist.")
        return

    items = [item for item in os.scandir(base_dir) if not item.is_dir()]
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        futures = [executor.submit(process_file, item, base_dir, simulation) for item in tqdm(items, desc="Processing files")]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("Usage: python organize.py [directory] [options]")
        print("Options:")
        print("  -v, --verbose          Enable detailed logging")
        print("  -s, --simulate         Simulate changes without modifying files")
        print("  --threads=N, -t N      Limit the number of threads for concurrent processing")
        print("  -h, --help             Display help documentation")

    verbosity = any(arg in args for arg in ("-v", "--verbose"))
    simulation = any(arg in args for arg in ("-s", "--simulate", "--dry-run"))

    # Get the base directory
    base_dir = next((arg for arg in args if not arg.startswith("-")), os.getcwd())

    organize_downloads(base_dir, verbosity, simulation)
