
"""
Download Organizer Script
==========================
This script organizes files from a specified directory (`base_dir`) into categorized subdirectories based on their types or names.
It supports extracting archive files, grouping files into directories, and performing file integrity checks.

Key Features:
-------------
1. **Archive Support**: Extracts `.zip`, `.tar`, `.7z`, `.rar`, `.gz`, `.bz2`, and `.xz` files.
2. **File Grouping**: Groups files based on simplified names (e.g., library names and versions).
3. **Integrity Check**: Computes MD5, SHA256, and SHA512 hashes for files.
4. **Simulation Mode**: Allows a dry run to see what actions would be taken without making changes.
5. **Concurrency**: Uses multithreading for faster processing of multiple files.
6. **Logging**: Logs operations with rotating file support to avoid bloated log files.
7. **Retry Mechanism**: Retries archive extraction up to 3 times in case of failure.
8. **Password-Protected Archives**: Supports archives with optional passwords.

Command Template:
-----------------
python organizer.py -c <config_path> -l <log_level>

Variables in Config File (`config.yaml`):
-----------------------------------------
- **base_dir**: The directory containing files to organize.
- **output_dir**: The directory where organized files will be placed.
- **simulate**: (Optional) `True` to simulate actions without making changes.
- **integrity**: (Optional) `True` to enable file integrity checks.
- **password**: (Optional) Password for password-protected archives. Use `PROMPT` to enter manually.
- **file_filter**: (Optional) Regex pattern to filter files.
- **max_threads**: (Optional) Maximum number of threads for processing files.
- **log_level**: (Optional) Logging verbosity level (DEBUG, INFO, WARNING, ERROR).
"""

import os
import re
import tarfile
import zipfile
import hashlib
import logging
import shutil
import concurrent.futures
from typing import Optional, Dict
from tqdm import tqdm
from pathlib import Path
import yaml
import py7zr
import rarfile
import gzip
import bz2
import lzma
from termcolor import colored
from retry import retry
import multiprocessing
import getpass
from logging.handlers import RotatingFileHandler
import argparse

# Global mapping of archive handlers for various formats
ARCHIVE_HANDLERS = {
    ".tar": tarfile.open,
    ".zip": zipfile.ZipFile,
    ".7z": py7zr.SevenZipFile,
    ".rar": rarfile.RarFile,
    ".gz": gzip.open,
    ".bz2": bz2.open,
    ".xz": lzma.open,
}

# Default configurations
DEFAULT_CONFIG = {
    "base_dir": "~/Downloads",  # Default directory
    "output_dir": "~/Organized_Files",
    "simulate": False,
    "integrity": False,
    "password": None,
    "file_filter": ".*",
    "max_threads": 4,
    "log_level": "INFO",
}

# Dynamically resolve the base directory to handle case sensitivity
def resolve_base_dir(base_dir: str) -> Path:
    """
    Dynamically resolves the 'Downloads' directory on Linux systems, handling case sensitivity.

    Args:
        base_dir (str): The base directory provided in the configuration.

    Returns:
        Path: A valid Path object pointing to the resolved base directory.
    """
    base_path = Path(base_dir).expanduser()
    parent_dir = base_path.parent if base_path.parent.is_dir() else Path.home()

    # Check for both case variations
    candidates = [parent_dir / "Downloads", parent_dir / "downloads"]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    # Fallback: Use the provided base_dir if no match
    return base_path

# Logging configuration with rotating file support
def configure_logging(log_level: str, log_file: Optional[str] = None) -> None:
    """
    Configures logging for the script.

    Args:
        log_level (str): Logging level (e.g., DEBUG, INFO, WARNING, ERROR).
        log_file (Optional[str]): File to store logs. If None, logs are printed to the console.
    """
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    log_level = getattr(logging, log_level.upper(), logging.WARNING)
    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)

# Validate configuration for required keys and directory validity
def validate_config(config: Dict) -> None:
    """
    Validates the configuration file for required keys and valid directories.

    Args:
        config (Dict): Configuration dictionary loaded from `config.yaml`.

    Raises:
        ValueError: If a required key is missing or a directory path is invalid.
    """
    required_keys = ["base_dir", "output_dir"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    if not Path(config["output_dir"]).expanduser().is_dir():
        raise ValueError("Invalid output directory path.")

# Simplify file names for consistent grouping
def simplify_name(file_name: str) -> str:
    """
    Simplifies file names by extracting base names and versions.

    Args:
        file_name (str): Original file name.

    Returns:
        str: Simplified name for grouping purposes.
    """
    base_name = os.path.splitext(file_name)[0].replace(" ", "_")
    match = re.match(r"([a-zA-Z0-9]+)[-_]?([0-9]+(?:\.[0-9]+)*)?[-_]?.*", base_name)
    if match:
        library, version = match.group(1), match.group(2) or ""
        return f"{library}-{version}" if version else library
    return base_name

# Check if a file is a supported archive format
def is_supported_archive(file_path: str) -> bool:
    """
    Determines if a file is a supported archive format.

    Args:
        file_path (str): Path to the file.

    Returns:
        bool: True if the file is a supported archive, False otherwise.
    """
    return Path(file_path).suffix.lower() in ARCHIVE_HANDLERS

# Ensure required directories exist
def ensure_directories_exist(group_folder: Path, specific_folder: Path) -> None:
    """
    Creates directories if they do not already exist.

    Args:
        group_folder (Path): General group directory path.
        specific_folder (Path): Specific file group directory path.
    """
    group_folder.mkdir(parents=True, exist_ok=True)
    specific_folder.mkdir(parents=True, exist_ok=True)

# Extract archive files with retry support
@retry(Exception, tries=3, delay=2)
def extract_file(file_path: str, extract_to: str, password: Optional[str] = None) -> None:
    """
    Extracts supported archive files to a specified directory.

    Args:
        file_path (str): Path to the archive file.
        extract_to (str): Directory to extract contents to.
        password (Optional[str]): Password for encrypted archives, if any.
    """
    file_extension = Path(file_path).suffix.lower()

    if file_extension not in ARCHIVE_HANDLERS:
        logging.error(f"Unsupported archive format: {file_path}")
        return

    try:
        handler = ARCHIVE_HANDLERS[file_extension]
        with handler(file_path, 'r') as archive:
            if hasattr(archive, 'extractall'):
                archive.extractall(path=extract_to, pwd=password.encode() if password else None)
            else:
                output_path = Path(extract_to) / Path(file_path).stem
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(archive, f_out)
        logging.info(f"Extracted: {file_path} to {extract_to}")
    except Exception as e:
        logging.error(f"Failed to extract {file_path}: {e}", exc_info=True)

# Calculate file integrity checksums
def integrity_check(file_path: str) -> Dict[str, str]:
    """
    Calculates MD5, SHA256, and SHA512 hashes for a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        Dict[str, str]: Dictionary of calculated hashes.
    """
    hashes = {"MD5": hashlib.md5(), "SHA256": hashlib.sha256(), "SHA512": hashlib.sha512()}
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):  # Larger chunks for performance
            for hash_obj in hashes.values():
                hash_obj.update(chunk)
    return {key: hash_obj.hexdigest() for key, hash_obj in hashes.items()}

# Process a single file for extraction, grouping, or moving
def process_file(
    item: os.DirEntry,
    output_dir: Path,
    simulate: bool,
    integrity: bool,
    password: Optional[str] = None
) -> None:
    """
    Processes an individual file: extracts, moves, or logs based on configuration.

    Args:
        item (os.DirEntry): File to process.
        output_dir (Path): Base output directory for organized files.
        simulate (bool): If True, simulates actions without making changes.
        integrity (bool): If True, performs integrity checks.
        password (Optional[str]): Password for password-protected archives, if any.
    """
    try:
        folder_name = simplify_name(item.name)
        group_folder = output_dir / folder_name.split("-")[0]
        specific_folder = group_folder / folder_name
        ensure_directories_exist(group_folder, specific_folder)

        if is_supported_archive(item.path):
            if simulate:
                logging.info(f"Simulating extraction of {item.name} to {specific_folder}")
                return
            extract_file(item.path, str(specific_folder), password=password)
            if integrity:
                checksums = integrity_check(item.path)
                logging.info(f"Integrity check for {item.name}: {checksums}")
        else:
            destination = specific_folder / item.name
            if simulate:
                logging.info(f"Simulating move of {item.name} to {specific_folder}")
                return
            shutil.move(item.path, destination)
    except Exception as e:
        logging.error(f"Failed to process {item.name}: {e}", exc_info=True)

# Main function for organizing downloads
def organize_downloads(config: Dict) -> None:
    """
    Main function for organizing files based on the provided configuration.

    Args:
        config (Dict): Configuration dictionary loaded from `config.yaml`.
    """
    # Dynamically resolve the base_dir
    base_dir = resolve_base_dir(config["base_dir"])
    output_dir = Path(config["output_dir"]).expanduser()
    simulate = config.get("simulate", False)
    integrity = config.get("integrity", False)
    password = config.get("password", None)
    if password == "PROMPT":
        password = getpass.getpass("Enter archive password: ")
    file_filter = re.compile(config.get("file_filter", ".*"))

    # Check base directory existence
    if not base_dir.is_dir() or not os.access(base_dir, os.R_OK):
        logging.error(colored(f"Base directory '{base_dir}' is invalid or inaccessible.", "red"))
        return

    # Scan items and process
    items = [item for item in os.scandir(base_dir) if not item.is_dir() and file_filter.search(item.name)]
    max_threads = min(len(items), multiprocessing.cpu_count(), config.get("max_threads", 4))

    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        list(
            tqdm(
                executor.map(lambda x: process_file(x, output_dir, simulate, integrity, password), items),
                total=len(items),
                desc="Processing Files"
            )
        )

# Parse command-line arguments
def parse_arguments() -> Dict:
    """
    Parses command-line arguments for the script.

    Returns:
        Dict: Parsed arguments as a dictionary.
    """
    parser = argparse.ArgumentParser(description="Organize and process archive files.")
    parser.add_argument("-c", "--config", required=True, help="Path to the configuration file.")
    parser.add_argument("-l", "--log", default="INFO", help="Log level (default: INFO).")
    return vars(parser.parse_args())

# Entry point of the script
if __name__ == "__main__":
    """
    Entry point of the script. Reads the configuration, validates it, and starts the organization process.
    """
    try:
        args = parse_arguments()
        configure_logging(args["log"], log_file="organize.log")

        # Load configuration
        try:
            with open(args["config"], "r") as config_file:
                config = yaml.safe_load(config_file)
        except FileNotFoundError:
            logging.warning("Config file not found. Using default settings.")
            config = DEFAULT_CONFIG

        validate_config(config)
        organize_downloads(config)
    except Exception as e:
        logging.error(colored(f"Unexpected error: {e}", "red"), exc_info=True)
