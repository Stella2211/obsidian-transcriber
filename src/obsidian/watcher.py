"""File system watcher for Obsidian vault"""

import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from src.audio.utils import is_audio_file
from src.constants import AUDIO_EXTENSIONS
from src.hooks.runner import HooksRunner
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AudioFileHandler(FileSystemEventHandler):
    """Handler for audio file system events"""

    def __init__(
        self,
        process_callback: Callable[[Path], None],
        hooks_runner: Optional[HooksRunner] = None,
    ):
        """
        Initialize handler

        Args:
            process_callback: Callback function to process audio files
            hooks_runner: Optional hooks runner for executing hooks
        """
        self.process_callback = process_callback
        self.hooks_runner = hooks_runner
        super().__init__()

    def _handle_file(self, path: Path) -> None:
        """
        Handle a detected file

        Args:
            path: Path to the detected file
        """
        # Run on_file_detected hook for all files
        if self.hooks_runner:
            result = self.hooks_runner.on_file_detected(path)
            if self.hooks_runner.should_abort(result):
                logger.warning(f"Aborting processing due to hook failure: {path}")
                return

        # Check if it's an audio file
        if is_audio_file(path):
            logger.info(f"Audio file detected: {path}")

            # Run on_audio_detected hook
            if self.hooks_runner:
                result = self.hooks_runner.on_audio_detected(path)
                if self.hooks_runner.should_abort(result):
                    logger.warning(f"Aborting processing due to hook failure: {path}")
                    return

            # Process the audio file
            self.process_callback(path)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event"""
        if not event.is_directory:
            path = Path(event.src_path)
            logger.debug(f"File created: {path}")
            # Wait a bit to ensure file is fully written
            time.sleep(2)
            self._handle_file(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification event"""
        if not event.is_directory:
            path = Path(event.src_path)
            if is_audio_file(path):
                logger.debug(f"Audio file modified: {path}")
                # Wait a bit to ensure file is fully written
                time.sleep(2)
                self._handle_file(path)


class VaultWatcher:
    """Watcher for Obsidian vault directory"""

    def __init__(
        self,
        vault_path: Path,
        process_callback: Callable[[Path], None],
        hooks_runner: Optional[HooksRunner] = None,
    ):
        """
        Initialize vault watcher

        Args:
            vault_path: Path to the Obsidian vault
            process_callback: Callback function to process audio files
            hooks_runner: Optional hooks runner for executing hooks
        """
        self.vault_path = vault_path
        self.process_callback = process_callback
        self.hooks_runner = hooks_runner
        self.observer: Optional[Observer] = None
        logger.info(f"Initialized vault watcher for: {vault_path}")

    def scan_existing_files(self) -> None:
        """Scan and process existing audio files in the vault"""
        logger.info(f"Scanning existing audio files in: {self.vault_path}")

        audio_files = []
        for ext in AUDIO_EXTENSIONS:
            pattern = f"*{ext}"
            audio_files.extend(self.vault_path.rglob(pattern))

        logger.info(f"Found {len(audio_files)} audio files")

        for audio_path in audio_files:
            try:
                # Run on_audio_detected hook
                if self.hooks_runner:
                    result = self.hooks_runner.on_audio_detected(audio_path)
                    if self.hooks_runner.should_abort(result):
                        logger.warning(
                            f"Skipping file due to hook failure: {audio_path}"
                        )
                        continue

                self.process_callback(audio_path)
            except Exception as e:
                logger.error(f"Failed to process {audio_path}: {e}")

    def start(self) -> None:
        """Start watching the vault directory"""
        if self.observer is not None:
            logger.warning("Watcher already running")
            return

        logger.info("Starting vault watcher")
        event_handler = AudioFileHandler(
            self.process_callback,
            hooks_runner=self.hooks_runner,
        )
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.vault_path), recursive=True)
        self.observer.start()
        logger.info("Vault watcher started")

    def stop(self) -> None:
        """Stop watching the vault directory"""
        if self.observer is None:
            logger.warning("Watcher not running")
            return

        logger.info("Stopping vault watcher")
        self.observer.stop()
        self.observer.join()
        self.observer = None
        logger.info("Vault watcher stopped")

    def run_forever(self) -> None:
        """Run the watcher forever (blocking)"""
        self.start()
        logger.info(f"Watching for audio files in: {self.vault_path}")
        logger.info(f"Supported formats: {', '.join(AUDIO_EXTENSIONS)}")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()
