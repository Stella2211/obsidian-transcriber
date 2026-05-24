"""Audio chunking for files exceeding Groq's size limit"""

import math
import os
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Any

from pydub import AudioSegment

from src.constants import (
    MAX_CHUNK_SIZE_MB,
    DEFAULT_CHUNK_OVERLAP_SECONDS,
    CHUNK_SAMPLE_RATE,
    CHUNK_CHANNELS,
    CHUNK_BITRATE_KBPS,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AudioChunker:
    """Handles splitting large audio files into chunks for Groq API"""

    def __init__(self, overlap_seconds: int = DEFAULT_CHUNK_OVERLAP_SECONDS):
        """
        Initialize the audio chunker

        Args:
            overlap_seconds: Overlap duration between chunks (default: 10 seconds)
        """
        self.max_size_bytes = MAX_CHUNK_SIZE_MB * 1024 * 1024
        self.overlap_seconds = overlap_seconds
        self._temp_files: List[Path] = []

    def needs_chunking(self, audio_path: Path) -> bool:
        """
        Check if audio file needs to be chunked

        Args:
            audio_path: Path to the audio file

        Returns:
            True if file exceeds size limit
        """
        file_size = os.path.getsize(audio_path)
        return file_size > self.max_size_bytes

    def get_file_size_mb(self, audio_path: Path) -> float:
        """Get file size in MB"""
        return os.path.getsize(audio_path) / (1024 * 1024)

    def split_audio(
        self,
        audio_path: Path,
        progress_callback: Optional[Callable[[str, Any], None]] = None,
    ) -> List[Tuple[float, float, Path]]:
        """
        Split audio file into chunks if needed

        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback for progress updates

        Returns:
            List of (start_seconds, end_seconds, chunk_path) tuples
        """
        file_size = os.path.getsize(audio_path)

        if file_size <= self.max_size_bytes:
            logger.info(
                f"File {audio_path.name} is within size limit, no chunking needed"
            )
            return [(0, 0, audio_path)]

        logger.info(
            f"File {audio_path.name} ({file_size / 1024 / 1024:.1f}MB) exceeds "
            f"{MAX_CHUNK_SIZE_MB}MB limit, chunking required"
        )

        if progress_callback:
            progress_callback("音声ファイルを分割中", None)

        # Load audio and downsample to 16kHz mono. Groq downsamples to 16kHz
        # mono internally, so this is lossless for transcription quality while
        # making the exported chunk size predictable from the bitrate alone.
        audio = AudioSegment.from_file(audio_path)
        audio = audio.set_frame_rate(CHUNK_SAMPLE_RATE).set_channels(CHUNK_CHANNELS)
        duration_seconds = len(audio) / 1000.0

        # Derive the maximum safe chunk duration from the *output* bitrate, not
        # the input file size. A low-bitrate source (e.g. 64kbps AAC) re-encodes
        # to a larger file, so sizing chunks by the input ratio can produce
        # chunks that exceed the API limit (HTTP 413). Computing from the export
        # bitrate guarantees each chunk stays under MAX_CHUNK_SIZE_MB.
        bytes_per_second = (CHUNK_BITRATE_KBPS * 1000) / 8
        # 0.95 safety margin for MP3 container/header overhead and VBR variance.
        max_chunk_seconds = (self.max_size_bytes / bytes_per_second) * 0.95

        # Distribute duration evenly across the minimum number of chunks needed,
        # then cap at the safe maximum (and floor at 30s to avoid tiny chunks).
        num_chunks = max(1, math.ceil(duration_seconds / max_chunk_seconds))
        effective_duration = duration_seconds + (
            self.overlap_seconds * (num_chunks - 1)
        )
        chunk_duration_ms = int((effective_duration / num_chunks) * 1000)
        chunk_duration_ms = min(chunk_duration_ms, int(max_chunk_seconds * 1000))
        chunk_duration_ms = max(chunk_duration_ms, 30000)

        overlap_ms = self.overlap_seconds * 1000
        chunks: List[Tuple[float, float, Path]] = []

        start_ms = 0
        chunk_index = 0

        while start_ms < len(audio):
            end_ms = min(start_ms + chunk_duration_ms, len(audio))
            chunk = audio[start_ms:end_ms]

            # Create temporary file for chunk
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False,
                prefix=f"chunk_{chunk_index:03d}_",
            )
            chunk_path = Path(temp_file.name)
            temp_file.close()

            # Export chunk as 16kHz mono MP3 at the configured bitrate.
            chunk.export(chunk_path, format="mp3", bitrate=f"{CHUNK_BITRATE_KBPS}k")
            self._temp_files.append(chunk_path)

            start_seconds = start_ms / 1000.0
            end_seconds = end_ms / 1000.0

            chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
            if chunk_size_mb > MAX_CHUNK_SIZE_MB:
                logger.warning(
                    f"Chunk {chunk_index} is {chunk_size_mb:.1f}MB, which exceeds "
                    f"the {MAX_CHUNK_SIZE_MB}MB target; transcription may fail"
                )

            chunks.append((start_seconds, end_seconds, chunk_path))
            logger.debug(
                f"Created chunk {chunk_index}: {start_seconds:.1f}s - {end_seconds:.1f}s "
                f"({chunk_size_mb:.1f}MB)"
            )

            chunk_index += 1

            # Move to next chunk with overlap
            # Subtract overlap from the next start position
            next_start = end_ms - overlap_ms
            if next_start <= start_ms:
                # Prevent infinite loop if chunk is too small
                next_start = end_ms
            start_ms = next_start

            # Stop if we've covered the entire audio
            if end_ms >= len(audio):
                break

        logger.info(
            f"Split audio into {len(chunks)} chunks (overlap: {self.overlap_seconds}s)"
        )

        return chunks

    def cleanup(self) -> None:
        """Remove all temporary chunk files"""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up {temp_file}: {e}")
        self._temp_files.clear()

    def __del__(self) -> None:
        """Cleanup on object destruction"""
        self.cleanup()
