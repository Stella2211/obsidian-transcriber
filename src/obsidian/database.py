"""Database for tracking processed files"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any, List
from enum import Enum

from src.utils.logging import get_logger

logger = get_logger(__name__)

# Database schema version
SCHEMA_VERSION = "1.0.0"


class ProcessingStatus(Enum):
    """Processing status for files"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProcessedFilesDatabase:
    """Database for tracking processed audio files"""

    def __init__(self, db_path: Path):
        """
        Initialize database

        Args:
            db_path: Path to the database JSON file
        """
        self.db_path = db_path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load database from file"""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)

                # Initialize if empty or invalid structure
                if not self.data or "version" not in self.data:
                    self._initialize_schema()
                else:
                    file_count = len(self.data.get("files", {}))
                    logger.info(
                        f"Loaded database v{self.data['version']} with {file_count} files"
                    )

            except Exception as e:
                logger.error(f"Failed to load database: {e}")
                self._initialize_schema()
        else:
            logger.info("Database file does not exist, creating new database")
            self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Initialize database schema"""
        self.data = {
            "version": SCHEMA_VERSION,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "statistics": {
                "total_processed": 0,
                "total_failed": 0,
                "total_size_bytes": 0,
                "total_duration_seconds": 0,
            },
            "files": {},
        }
        logger.info(f"Initialized new database schema v{SCHEMA_VERSION}")

    def save(self) -> None:
        """Save database to file"""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Update last_updated timestamp
            self.data["last_updated"] = datetime.now().isoformat()

            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved database with {len(self.data['files'])} files")
        except Exception as e:
            logger.error(f"Failed to save database: {e}")
            raise

    def get_file_hash(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of a file

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash string
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def is_processed(self, file_path: Path) -> bool:
        """
        Check if a file has been successfully processed

        Args:
            file_path: Path to the file

        Returns:
            True if file has been processed with same hash
        """
        str_path = str(file_path)

        files = self.data.get("files", {})
        if str_path not in files:
            return False

        file_entry = files[str_path]

        # Check status
        if file_entry.get("status") != ProcessingStatus.COMPLETED.value:
            return False

        # Check if file hash matches
        try:
            current_hash = self.get_file_hash(file_path)
            stored_hash = file_entry.get("hash")
            return current_hash == stored_hash
        except Exception as e:
            logger.warning(f"Failed to check file hash: {e}")
            return False

    def add_processed_file(
        self,
        file_path: Path,
        markdown_path: Path,
        summary_path: Optional[Path] = None,
        duration_seconds: Optional[float] = None,
        file_size_bytes: Optional[int] = None,
    ) -> None:
        """
        Add a successfully processed file to the database

        Args:
            file_path: Path to the audio file
            markdown_path: Path to the transcription markdown
            summary_path: Optional path to the summary markdown
            duration_seconds: Optional audio duration in seconds
            file_size_bytes: Optional file size in bytes
        """
        try:
            file_hash = self.get_file_hash(file_path)
            str_path = str(file_path)

            # Check if this was previously failed
            was_failed = False
            if str_path in self.data["files"]:
                old_entry = self.data["files"][str_path]
                if old_entry.get("status") == ProcessingStatus.FAILED.value:
                    was_failed = True
                    self.data["statistics"]["total_failed"] = max(
                        0, self.data["statistics"]["total_failed"] - 1
                    )

            self.data["files"][str_path] = {
                "hash": file_hash,
                "status": ProcessingStatus.COMPLETED.value,
                "processed_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "outputs": {
                    "transcription": str(markdown_path),
                    "summary": str(summary_path) if summary_path else None,
                },
                "metadata": {
                    "duration_seconds": duration_seconds,
                    "file_size_bytes": file_size_bytes,
                },
                "error": None,
            }

            # Update statistics
            if not was_failed:
                self.data["statistics"]["total_processed"] += 1
            if duration_seconds:
                self.data["statistics"]["total_duration_seconds"] += duration_seconds
            if file_size_bytes:
                self.data["statistics"]["total_size_bytes"] += file_size_bytes

            self.save()
            logger.info(f"Added processed file to database: {file_path}")
        except Exception as e:
            logger.error(f"Failed to add processed file to database: {e}")
            raise

    def add_failed_file(
        self, file_path: Path, error: str, file_size_bytes: Optional[int] = None
    ) -> None:
        """
        Add a failed file to the database

        Args:
            file_path: Path to the audio file
            error: Error message
            file_size_bytes: Optional file size in bytes
        """
        try:
            str_path = str(file_path)

            # Try to get file hash if file exists
            file_hash = None
            try:
                file_hash = self.get_file_hash(file_path)
            except:  # noqa: E722
                pass

            # Check if this was previously processed
            was_processed = False
            if str_path in self.data["files"]:
                old_entry = self.data["files"][str_path]
                if old_entry.get("status") == ProcessingStatus.COMPLETED.value:
                    was_processed = True
                    self.data["statistics"]["total_processed"] = max(
                        0, self.data["statistics"]["total_processed"] - 1
                    )

            self.data["files"][str_path] = {
                "hash": file_hash,
                "status": ProcessingStatus.FAILED.value,
                "processed_at": None,
                "updated_at": datetime.now().isoformat(),
                "outputs": {"transcription": None, "summary": None},
                "metadata": {"file_size_bytes": file_size_bytes},
                "error": error,
            }

            # Update statistics
            if not was_processed:
                self.data["statistics"]["total_failed"] += 1

            self.save()
            logger.info(f"Added failed file to database: {file_path}")
        except Exception as e:
            logger.error(f"Failed to add failed file to database: {e}")

    def get_processed_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get processed file information

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with processed file info or None
        """
        return self.data.get("files", {}).get(str(file_path))

    def remove_processed_file(self, file_path: Path) -> None:
        """
        Remove a file from the database

        Args:
            file_path: Path to the file
        """
        str_path = str(file_path)
        files = self.data.get("files", {})

        if str_path in files:
            file_entry = files[str_path]

            # Update statistics
            stats = self.data["statistics"]
            if file_entry.get("status") == ProcessingStatus.COMPLETED.value:
                stats["total_processed"] = max(0, stats["total_processed"] - 1)
                if file_entry.get("metadata", {}).get("duration_seconds"):
                    stats["total_duration_seconds"] = max(
                        0,
                        stats["total_duration_seconds"]
                        - file_entry["metadata"]["duration_seconds"],
                    )
                if file_entry.get("metadata", {}).get("file_size_bytes"):
                    stats["total_size_bytes"] = max(
                        0,
                        stats["total_size_bytes"]
                        - file_entry["metadata"]["file_size_bytes"],
                    )
            elif file_entry.get("status") == ProcessingStatus.FAILED.value:
                stats["total_failed"] = max(0, stats["total_failed"] - 1)

            del files[str_path]
            self.save()
            logger.info(f"Removed file from database: {file_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Dictionary with statistics
        """
        return self.data.get("statistics", {})

    def get_all_files(
        self, status: Optional[ProcessingStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all files with optional status filter

        Args:
            status: Optional status filter

        Returns:
            List of file entries with their paths
        """
        files = self.data.get("files", {})

        result = []
        for file_path, file_data in files.items():
            if status is None or file_data.get("status") == status.value:
                entry = file_data.copy()
                entry["path"] = file_path
                result.append(entry)

        return result

    def cleanup_orphaned_entries(self) -> int:
        """
        Remove database entries for files that no longer exist

        Returns:
            Number of entries removed
        """
        files = self.data.get("files", {})
        removed_count = 0

        for file_path in list(files.keys()):
            if not Path(file_path).exists():
                logger.info(f"Removing orphaned entry: {file_path}")
                self.remove_processed_file(Path(file_path))
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} orphaned database entries")

        return removed_count

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the database

        Returns:
            Dictionary with summary information
        """
        stats = self.get_statistics()
        files = self.data.get("files", {})

        # Count by status
        status_counts = {}
        for status in ProcessingStatus:
            status_counts[status.value] = sum(
                1 for f in files.values() if f.get("status") == status.value
            )

        # Format sizes
        total_gb = stats.get("total_size_bytes", 0) / (1024**3)
        total_hours = stats.get("total_duration_seconds", 0) / 3600

        return {
            "version": self.data.get("version"),
            "created_at": self.data.get("created_at"),
            "last_updated": self.data.get("last_updated"),
            "total_files": len(files),
            "status_breakdown": status_counts,
            "total_size_gb": round(total_gb, 2),
            "total_duration_hours": round(total_hours, 2),
            "statistics": stats,
        }
