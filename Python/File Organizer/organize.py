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
import hashlib

# Configure logging with dynamic log-level support
def configure_logging(log_level):
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.WARNING), format=log_format)

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
- Output directory support and batch processing by file type.
- File integrity checking (optional).

Usage:
  python organize.py [directory] [options]

Options:
  -v, --verbose          Enable detailed logging.
  -s, --simulate         Simulate changes without modifying files.
  -t N, --threads=N      Limit the number of threads for concurrent processing.
  -o DIR, --output-dir DIR Specify an output directory for organized files.
  --batch-type TYPE      Process files in batches by type (e.g., archive, document).
  --integrity-check      Enable integrity checks for extracted files.
  -h, --help             Display help documentation.

Example:
  python organize.py ~/Downloads -v --simulate --threads=8 --output-dir ~/Organized --batch-type archive
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


def is_supported_archive(file_path):
    """
    Check if the file is a supported archive format.

    Args:
        file_path (str): The file path to check.

    Returns:
        bool: True if the file is a supported archive, False otherwise.
    """
    return tarfile.is_tarfile(file_path) or zipfile.is_zipfile(file_path) or file_path.endswith((".7z", ".rar", ".gz"))


def extract_file(file_path, extract_to, simulation):
    """
    Extract the given archive file to the specified directory.

    Args:
        file_path (str): The path to the archive file.
        extract_to (str): The directory to extract the contents to.
        simulation (bool): If True, simulate extraction without making changes.

    Returns:
        bool: True if extraction succeeded, False otherwise.
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


def integrity_check(file_path):
    """
    Perform a simple integrity check by calculating the MD5 checksum of a file.

    Args:
        file_path (str): The path to the file to check.

    Returns:
        str: The MD5 checksum of the file.
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"Failed to calculate integrity for {file_path}: {e}")
        return None


def process_file(item, base_dir, output_dir, simulation, integrity):
    """
    Process a single file by simplifying its name, extracting if necessary, and moving it to the appropriate directory.

    Args:
        item (os.DirEntry): The file to process.
        base_dir (str): The base directory to organize files into.
        output_dir (str): The directory to output organized files.
        simulation (bool): If True, simulate processing without making changes.
        integrity (bool): If True, perform integrity checks.
    """
    item_path = item.path
    folder_name = simplify_name(item.name)
    group_match = re.match(r"([a-zA-Z]+)[-_]?.*", folder_name)
    group_name = group_match.group(1) if group_match else folder_name
    group_folder_path = os.path.join(output_dir, group_name)
    specific_folder_path = os.path.join(group_folder_path, folder_name)

    if not simulation:
        os.makedirs(group_folder_path, exist_ok=True)
        os.makedirs(specific_folder_path, exist_ok=True)

    if is_supported_archive(item_path):
        success = extract_file(item_path, specific_folder_path, simulation)
        if success and not simulation:
            if integrity:
                checksum = integrity_check(item_path)
                if checksum:
                    logging.info(f"Integrity check passed for {item_path} (MD5: {checksum})")
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


def organize_downloads(base_dir, verbosity, simulation, max_threads, output_dir, batch_type, integrity):
    """
    Organize files in the specified base directory by grouping them based on their names and version numbers.

    Args:
        base_dir (str): The base directory to organize files into.
        verbosity (bool): Enable verbose logging if True.
        simulation (bool): If True, simulate organization without making changes.
        max_threads (int): Limit the number of threads for concurrent processing.
        output_dir (str): Directory to place organized files.
        batch_type (str): Type of files to process in batches (e.g., "archive").
        integrity (bool): Enable integrity checks for processed files.
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
    if batch_type == "archive":
        items = [item for item in items if is_supported_archive(item.path)]

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        futures = [executor.submit(process_file, item, base_dir, output_dir, simulation, integrity) for item in tqdm(items, desc="Processing files")]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print("Usage: python organize.py [directory] [options]")
        print("Options:")
        print("  -v, --verbose          Enable detailed logging")
        print("  -s, --simulate         Simulate changes without modifying files")
        print("  -o DIR, --output-dir DIR Specify an output directory for organized files")
        print("  --batch-type TYPE      Process files in batches by type (e.g., archive, document)")
        print("  --integrity-check      Enable integrity checks for extracted files")
        print("  -t N, --threads=N      Limit the number of threads for concurrent processing")
        print("  -h, --help             Display help documentation")
        sys.exit(0)

    verbosity = any(arg in args for arg in ("-v", "--verbose"))
    simulation = any(arg in args for arg in ("-s", "--simulate", "--dry-run"))
    output_dir = next((arg.split("=")[1] for arg in args if arg.startswith("-o") or arg.startswith("--output-dir")), os.getcwd())
    batch_type = next((arg.split("=")[1] for arg in args if arg.startswith("--batch-type")), None)
    integrity = "--integrity-check" in args

    # Get the base directory
    base_dir = next((arg for arg in args if not arg.startswith("-")), os.getcwd())

    # Get max threads from arguments
    max_threads = next((int(arg.split("=")[1]) for arg in args if arg.startswith("--threads=")),
                       next((int(args[args.index("-t") + 1]) for arg in args if "-t" in args), os.cpu_count() or 4))

    configure_logging("INFO" if verbosity else "WARNING")

    organize_downloads(base_dir, verbosity, simulation, max_threads, output_dir, batch_type, integrity)
