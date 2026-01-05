"""Main handler for processing audio files in Obsidian"""

from pathlib import Path
from typing import Optional

from src.transcription.service import TranscriptionService
from src.obsidian.database import ProcessedFilesDatabase
from src.obsidian.note import NoteGenerator
from src.hooks.config import HooksConfig
from src.hooks.runner import HooksRunner
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ObsidianTranscriptionHandler:
    """Main handler for processing audio files in Obsidian vault"""

    def __init__(
        self,
        groq_api_key: str,
        gemini_api_key: str,
        vault_path: Path,
        db_path: Path,
        create_summary: bool = True,
        chunk_overlap_seconds: int = 10,
        verbose: bool = False,
        hooks_config: Optional[HooksConfig] = None,
    ):
        """
        Initialize handler

        Args:
            groq_api_key: Groq API key for Whisper transcription
            gemini_api_key: Gemini API key for summarization
            vault_path: Path to the Obsidian vault
            db_path: Path to the database file
            create_summary: Whether to create summaries
            chunk_overlap_seconds: Overlap between audio chunks
            verbose: Enable verbose logging
            hooks_config: Optional hooks configuration
        """
        self.vault_path = vault_path
        self.create_summary = create_summary
        self.verbose = verbose
        self.hooks_config = hooks_config or HooksConfig()

        # Initialize services
        self.transcription_service = TranscriptionService(
            groq_api_key=groq_api_key,
            gemini_api_key=gemini_api_key,
            chunk_overlap_seconds=chunk_overlap_seconds,
            verbose=verbose,
        )
        self.database = ProcessedFilesDatabase(db_path)
        self.note_generator = NoteGenerator(vault_path)

        logger.info("Initialized Obsidian transcription handler")
        logger.info(f"Vault path: {vault_path}")
        logger.info(f"Database path: {db_path}")
        logger.info(
            f"Summary generation: {'enabled' if create_summary else 'disabled'}"
        )
        if hooks_config and hooks_config.has_enabled_hooks():
            logger.info("Hooks: enabled")

    def _create_progress_callback(self, audio_path: Path):
        """
        Create a progress callback function for updating progress notes

        Args:
            audio_path: Path to the audio file

        Returns:
            Callback function for progress updates
        """

        def callback(status: str, segment_info: Optional[tuple] = None):
            self.note_generator.update_progress_note(
                audio_path, status, segment_info=segment_info
            )

        return callback

    def _create_hooks_progress_callback(self, audio_path: Path):
        """
        Create a progress callback for hooks runner

        Args:
            audio_path: Path to the audio file

        Returns:
            Callback function for hooks progress updates
        """

        def callback(status: str, details: Optional[str] = None):
            self.note_generator.update_progress_note(audio_path, status, details=details)

        return callback

    def process_audio_file(self, audio_path: Path) -> bool:
        """
        Process a single audio file

        Args:
            audio_path: Path to the audio file

        Returns:
            True if processing was successful
        """
        logger.info(f"Processing audio file: {audio_path}")

        # Create progress note at start
        self.note_generator.update_progress_note(audio_path, "処理開始")

        # Create hooks runner with progress callback
        hooks_progress_callback = self._create_hooks_progress_callback(audio_path)
        hooks_runner = HooksRunner(
            self.hooks_config, progress_callback=hooks_progress_callback
        )

        try:
            # Check if already processed
            if self.database.is_processed(audio_path):
                logger.info(f"File already processed: {audio_path}")
                self.note_generator.delete_progress_note(audio_path)
                return True

            # Create progress callback
            progress_callback = self._create_progress_callback(audio_path)

            # Transcribe the audio
            logger.info("Starting transcription")
            self.note_generator.update_progress_note(audio_path, "文字起こし準備中")
            transcription = self.transcription_service.transcribe_file(
                audio_path, progress_callback=progress_callback
            )

            if not transcription:
                logger.error("Transcription returned empty result")
                self.note_generator.update_progress_note(
                    audio_path, "エラー", details="文字起こし結果が空でした"
                )
                return False

            # Create and save transcription note
            logger.info("Creating transcription note")
            self.note_generator.update_progress_note(
                audio_path, "文字起こしノート作成中"
            )
            transcription_content = self.note_generator.create_transcription_note(
                audio_path, transcription
            )

            transcription_path = audio_path.parent / f"{audio_path.stem}_文字起こし.md"
            self.note_generator.save_note(transcription_content, transcription_path)

            # Run on_transcription_complete hook
            result = hooks_runner.on_transcription_complete(
                audio_path, transcription_path
            )
            if hooks_runner.should_abort(result):
                logger.warning("Aborting due to on_transcription_complete hook failure")
                self.note_generator.update_progress_note(
                    audio_path,
                    "フックエラーで中断",
                    details="on_transcription_complete フックが失敗しました",
                )
                return False

            # Create summary if enabled
            summary_path: Optional[Path] = None
            if self.create_summary:
                logger.info("Generating summary")
                self.note_generator.update_progress_note(audio_path, "要約生成中")
                summary = self.transcription_service.generate_summary(
                    transcription, audio_path
                )

                if summary:
                    logger.info("Creating summary note")
                    self.note_generator.update_progress_note(
                        audio_path, "要約ノート作成中"
                    )
                    summary_content = self.note_generator.create_summary_note(
                        audio_path, transcription, summary
                    )

                    summary_path = audio_path.parent / f"{audio_path.stem}_要約.md"
                    self.note_generator.save_note(summary_content, summary_path)

                    # Run on_summary_complete hook (no progress note update)
                    result = hooks_runner.on_summary_complete(
                        audio_path, transcription_path, summary_path
                    )
                    if hooks_runner.should_abort(result):
                        logger.warning(
                            "Aborting due to on_summary_complete hook failure"
                        )
                        # Note: files are already saved, so just log the error
                else:
                    logger.warning("Summary generation failed")

            # Get file metadata for database
            try:
                from src.audio.utils import get_audio_duration

                duration = get_audio_duration(audio_path)
                file_size = audio_path.stat().st_size
            except:  # noqa: E722
                duration = None
                file_size = None

            # Update database
            self.database.add_processed_file(
                audio_path,
                transcription_path,
                summary_path,
                duration_seconds=duration,
                file_size_bytes=file_size,
            )

            # Delete progress note on success
            self.note_generator.delete_progress_note(audio_path)

            logger.info(f"Successfully processed: {audio_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to process audio file: {e}", exc_info=True)
            # Update progress note with error info
            self.note_generator.update_progress_note(
                audio_path, "エラー発生", details=str(e)
            )
            return False

    def reprocess_file(self, audio_path: Path) -> bool:
        """
        Force reprocess a file, ignoring the database

        Args:
            audio_path: Path to the audio file

        Returns:
            True if processing was successful
        """
        logger.info(f"Force reprocessing file: {audio_path}")

        # Remove from database if exists
        self.database.remove_processed_file(audio_path)

        # Process the file
        return self.process_audio_file(audio_path)
