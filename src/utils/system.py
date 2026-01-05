"""System utility functions"""

import subprocess
from pathlib import Path


def check_ffmpeg() -> bool:
    """
    Check if FFmpeg is installed on the system

    Returns:
        True if FFmpeg is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def ensure_ffmpeg() -> None:
    """
    Ensure FFmpeg is installed, raise error with instructions if not

    Raises:
        RuntimeError: If FFmpeg is not installed
    """
    if not check_ffmpeg():
        raise RuntimeError(
            "FFmpeg is not installed. FFmpeg is required for processing non-WAV audio formats.\n"
            "Installation instructions:\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  macOS: brew install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


def ensure_directory(path: Path) -> None:
    """
    Ensure a directory exists, create if it doesn't

    Args:
        path: Directory path to ensure exists
    """
    path.mkdir(parents=True, exist_ok=True)


def validate_file_path(path: Path, must_exist: bool = True) -> Path:
    """
    Validate a file path

    Args:
        path: Path to validate
        must_exist: Whether the file must exist

    Returns:
        Validated path

    Raises:
        FileNotFoundError: If must_exist is True and file doesn't exist
        ValueError: If path is not a file
    """
    if must_exist and not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.exists() and not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    return path


def validate_directory_path(path: Path, must_exist: bool = True) -> Path:
    """
    Validate a directory path

    Args:
        path: Path to validate
        must_exist: Whether the directory must exist

    Returns:
        Validated path

    Raises:
        FileNotFoundError: If must_exist is True and directory doesn't exist
        ValueError: If path is not a directory
    """
    if must_exist and not path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if path.exists() and not path.is_dir():
        raise ValueError(f"Path is not a directory: {path}")

    return path
