"""Groq Whisper API client for audio transcription"""

from pathlib import Path
from typing import Optional

from groq import Groq, omit

from src.api.retry import retry_with_backoff, RetryableError
from src.constants import (
    GROQ_TRANSCRIPTION_MODEL,
    GROQ_TIMEOUT,
    MAX_RETRIES,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GroqClient:
    """Client for Groq Whisper API transcription"""

    def __init__(self, api_key: str):
        """
        Initialize the Groq client

        Args:
            api_key: Groq API key
        """
        self.client = Groq(api_key=api_key)
        self.model = GROQ_TRANSCRIPTION_MODEL

    def transcribe_audio(
        self,
        audio_path: Path,
        language: str = "ja",
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe an audio file using Groq Whisper

        Args:
            audio_path: Path to the audio file
            language: Language code (default: Japanese)
            prompt: Optional context prompt for better accuracy

        Returns:
            Transcribed text

        Raises:
            Exception: If transcription fails after all retries
        """
        logger.info(f"Transcribing audio: {audio_path.name}")

        def do_transcription() -> str:
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=self.model,
                    language=language,
                    prompt=prompt if prompt is not None else omit,
                    response_format="text",
                    temperature=0.0,
                )

            # Handle response - can be string or object with text attribute
            if isinstance(transcription, str):
                result = transcription.strip()
            else:
                result = transcription.text.strip() if transcription.text else ""

            if not result:
                raise RetryableError("Empty transcription response")

            return result

        try:
            result = retry_with_backoff(
                do_transcription,
                max_retries=MAX_RETRIES,
                timeout=GROQ_TIMEOUT,
            )
            logger.info(f"Successfully transcribed: {audio_path.name}")
            return result
        except Exception as e:
            logger.error(f"Failed to transcribe {audio_path.name}: {e}")
            raise

    def transcribe_audio_segment(
        self,
        audio_path: Path,
        start_seconds: float,
        end_seconds: float,
        language: str = "ja",
    ) -> str:
        """
        Transcribe an audio segment with timing context

        Args:
            audio_path: Path to the audio segment file
            start_seconds: Start time of segment in original audio
            end_seconds: End time of segment in original audio
            language: Language code

        Returns:
            Transcribed text with timing info
        """
        prompt = f"このセグメントは元の音声の{start_seconds:.1f}秒から{end_seconds:.1f}秒の部分です。"

        return self.transcribe_audio(
            audio_path=audio_path,
            language=language,
            prompt=prompt,
        )
