"""Audio transcription service using Groq Whisper and Gemini"""

from pathlib import Path
from typing import Optional, Callable

from src.api.groq_client import GroqClient
from src.api.client import GeminiClient
from src.audio.chunking import AudioChunker
from src.audio.utils import get_audio_duration
from src.constants import MAX_TRANSCRIPTION_PREVIEW_LENGTH, DEFAULT_CHUNK_OVERLAP_SECONDS
from src.utils.logging import get_logger
from src.utils.text import merge_all_segments

logger = get_logger(__name__)


class TranscriptionService:
    """Service for transcribing audio files using Groq Whisper"""

    def __init__(
        self,
        groq_api_key: str,
        gemini_api_key: str,
        chunk_overlap_seconds: int = DEFAULT_CHUNK_OVERLAP_SECONDS,
        verbose: bool = False,
    ):
        """
        Initialize transcription service

        Args:
            groq_api_key: Groq API key for Whisper transcription
            gemini_api_key: Gemini API key for summarization
            chunk_overlap_seconds: Overlap between audio chunks (default: 10 seconds)
            verbose: Enable verbose logging
        """
        self.groq_client = GroqClient(groq_api_key)
        self.gemini_client = GeminiClient(gemini_api_key)
        self.chunker = AudioChunker(overlap_seconds=chunk_overlap_seconds)
        self.verbose = verbose
        logger.info("Initialized transcription service (Groq Whisper + Gemini)")

    def transcribe_file(
        self,
        audio_path: Path,
        progress_callback: Optional[
            Callable[[str, Optional[tuple[int, int]]], None]
        ] = None,
    ) -> str:
        """
        Transcribe an audio file using Groq Whisper

        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback function for progress updates
                               Takes (status: str, segment_info: Optional[tuple[current, total]])

        Returns:
            Transcribed text
        """
        logger.info(f"Starting transcription for: {audio_path}")

        try:
            duration = get_audio_duration(audio_path)
            logger.info(f"Audio duration: {duration:.2f} seconds")

            if self.chunker.needs_chunking(audio_path):
                file_size_mb = self.chunker.get_file_size_mb(audio_path)
                logger.info(f"File size ({file_size_mb:.1f}MB) exceeds limit, chunking required")
                return self._transcribe_with_chunking(audio_path, progress_callback)
            else:
                if progress_callback:
                    progress_callback("文字起こし中", None)
                return self._transcribe_direct(audio_path)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def _transcribe_direct(self, audio_path: Path) -> str:
        """
        Transcribe audio file directly without chunking

        Args:
            audio_path: Path to the audio file

        Returns:
            Transcribed text
        """
        logger.info("Transcribing audio directly (no chunking)")
        return self.groq_client.transcribe_audio(audio_path)

    def _transcribe_with_chunking(
        self,
        audio_path: Path,
        progress_callback: Optional[
            Callable[[str, Optional[tuple[int, int]]], None]
        ] = None,
    ) -> str:
        """
        Transcribe audio file with chunking for large files

        Args:
            audio_path: Path to the audio file
            progress_callback: Optional callback function for progress updates

        Returns:
            Transcribed text
        """
        logger.info("Transcribing audio with chunking")

        if progress_callback:
            progress_callback("音声ファイルを分割中", None)

        try:
            # Split audio into chunks
            chunks = self.chunker.split_audio(audio_path, progress_callback)
            total_chunks = len(chunks)
            logger.info(f"Audio split into {total_chunks} chunks")

            transcriptions = []
            for i, (start, end, chunk_path) in enumerate(chunks):
                current_chunk = i + 1
                logger.info(f"Processing chunk {current_chunk}/{total_chunks}")

                if progress_callback:
                    progress_callback(
                        f"チャンク {current_chunk}/{total_chunks} を文字起こし中",
                        (current_chunk, total_chunks),
                    )

                try:
                    # Check if this is the original file (no chunking needed for single chunk)
                    if chunk_path == audio_path:
                        chunk_text = self.groq_client.transcribe_audio(chunk_path)
                    else:
                        chunk_text = self.groq_client.transcribe_audio_segment(
                            chunk_path, start, end
                        )
                    transcriptions.append(chunk_text)
                except Exception as e:
                    logger.error(f"Failed to transcribe chunk {current_chunk}: {e}")
                    transcriptions.append(
                        f"[チャンク {current_chunk} の文字起こしに失敗: {e}]"
                    )

            # Combine transcriptions with deduplication
            if progress_callback:
                progress_callback("チャンクを結合中（重複削除）", None)

            full_transcription, success_count, fail_count = merge_all_segments(
                transcriptions
            )

            logger.info(
                f"Transcription completed, total length: {len(full_transcription)} characters"
            )
            if total_chunks > 1:
                logger.info(
                    f"Deduplication: {success_count} successful, {fail_count} kept both versions"
                )

            return full_transcription

        finally:
            # Clean up temporary chunk files
            self.chunker.cleanup()

    def generate_summary(
        self, transcription: str, audio_path: Optional[Path] = None
    ) -> Optional[str]:
        """
        Generate a summary of the transcription using Gemini

        Args:
            transcription: The transcribed text
            audio_path: Optional path to the original audio file for context

        Returns:
            Summary text or None if generation fails
        """
        try:
            logger.info("Generating summary of transcription")

            # Truncate transcription if too long
            preview = transcription[:MAX_TRANSCRIPTION_PREVIEW_LENGTH]
            if len(transcription) > MAX_TRANSCRIPTION_PREVIEW_LENGTH:
                preview += "\n\n[文字起こしの続きは省略されています...]"

            # Add context if audio path is provided
            context = ""
            if audio_path:
                context = f"音声ファイル: {audio_path.name}"

            summary = self.gemini_client.summarize_text(preview, context)
            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return None
