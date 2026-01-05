"""Audio utility functions"""

from pathlib import Path
import soundfile as sf
from pydub import AudioSegment

from src.constants import AUDIO_EXTENSIONS
from src.utils.logging import get_logger

logger = get_logger(__name__)


def is_audio_file(path: Path) -> bool:
    """
    Check if a file is an audio file based on its extension

    Args:
        path: File path to check

    Returns:
        True if the file has an audio extension
    """
    return path.suffix.lower() in AUDIO_EXTENSIONS


def get_audio_duration(audio_path: Path) -> float:
    """
    Get the duration of an audio file in seconds

    Args:
        audio_path: Path to the audio file

    Returns:
        Duration in seconds
    """
    try:
        info = sf.info(str(audio_path))
        duration = info.duration
        logger.debug(f"Audio duration for {audio_path}: {duration:.2f} seconds")
        return duration
    except Exception as e:
        logger.warning(f"Failed to get duration with soundfile: {e}, trying pydub")
        try:
            audio = AudioSegment.from_file(str(audio_path))
            duration = audio.duration_seconds
            logger.debug(f"Audio duration for {audio_path}: {duration:.2f} seconds")
            return duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            raise


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to a human-readable string

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "1時間23分45秒")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}時間{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"


def get_file_size_mb(file_path: Path) -> float:
    """
    Get file size in megabytes

    Args:
        file_path: Path to the file

    Returns:
        File size in MB
    """
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return size_mb
