"""Tests for processed files database"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.obsidian.database import ProcessedFilesDatabase


class TestProcessedFilesDatabase(unittest.TestCase):
    """Test cases for ProcessedFilesDatabase"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_db.json"

    def test_init_new_database(self):
        """Test initializing a new database"""
        db = ProcessedFilesDatabase(self.db_path)
        self.assertIn("version", db.data)
        self.assertEqual(db.data["version"], "1.0.0")
        self.assertIn("files", db.data)
        self.assertEqual(db.data["files"], {})
        self.assertEqual(db.db_path, self.db_path)

    def test_load_existing_database(self):
        """Test loading an existing database"""
        # Create a test database file with proper schema
        test_data = {
            "version": "1.0.0",
            "created_at": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "statistics": {
                "total_processed": 1,
                "total_failed": 0,
                "total_size_bytes": 1000,
                "total_duration_seconds": 60,
            },
            "files": {
                "/test/file1.mp3": {
                    "hash": "test_hash",
                    "status": "completed",
                    "processed_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                    "outputs": {
                        "transcription": "/test/file1_文字起こし.md",
                        "summary": "/test/file1_要約.md",
                    },
                    "metadata": {"duration_seconds": 60, "file_size_bytes": 1000},
                    "error": None,
                }
            },
        }
        with open(self.db_path, "w") as f:
            json.dump(test_data, f)

        db = ProcessedFilesDatabase(self.db_path)
        self.assertEqual(db.data["version"], "1.0.0")
        self.assertEqual(len(db.data["files"]), 1)
        self.assertIn("/test/file1.mp3", db.data["files"])

    def test_save_database(self):
        """Test saving database to file"""
        db = ProcessedFilesDatabase(self.db_path)
        # Modify files in the database
        db.data["files"]["/test/file.mp3"] = {"hash": "test_hash"}
        db.save()

        # Verify file was written correctly
        with open(self.db_path, "r") as f:
            saved_data = json.load(f)
        self.assertIn("last_updated", saved_data)
        self.assertEqual(saved_data["files"]["/test/file.mp3"]["hash"], "test_hash")

    @patch("src.obsidian.database.ProcessedFilesDatabase.get_file_hash")
    def test_is_processed_true(self, mock_hash):
        """Test is_processed returns True for processed file"""
        mock_hash.return_value = "test_hash"

        db = ProcessedFilesDatabase(self.db_path)
        test_file = Path("/test/file.mp3")
        db.data["files"][str(test_file)] = {"hash": "test_hash", "status": "completed"}

        self.assertTrue(db.is_processed(test_file))

    @patch("src.obsidian.database.ProcessedFilesDatabase.get_file_hash")
    def test_is_processed_false_not_in_db(self, mock_hash):
        """Test is_processed returns False for unprocessed file"""
        mock_hash.return_value = "test_hash"

        db = ProcessedFilesDatabase(self.db_path)
        test_file = Path("/test/file.mp3")

        self.assertFalse(db.is_processed(test_file))

    @patch("src.obsidian.database.ProcessedFilesDatabase.get_file_hash")
    def test_is_processed_false_different_hash(self, mock_hash):
        """Test is_processed returns False for modified file"""
        mock_hash.return_value = "new_hash"

        db = ProcessedFilesDatabase(self.db_path)
        test_file = Path("/test/file.mp3")
        db.data["files"][str(test_file)] = {"hash": "old_hash", "status": "completed"}

        self.assertFalse(db.is_processed(test_file))

    @patch("src.obsidian.database.ProcessedFilesDatabase.get_file_hash")
    @patch("src.obsidian.database.ProcessedFilesDatabase.save")
    def test_add_processed_file(self, mock_save, mock_hash):
        """Test adding a processed file"""
        mock_hash.return_value = "test_hash"

        db = ProcessedFilesDatabase(self.db_path)
        audio_file = Path("/test/audio.mp3")
        markdown_file = Path("/test/audio_文字起こし.md")
        summary_file = Path("/test/audio_要約.md")

        db.add_processed_file(audio_file, markdown_file, summary_file)

        self.assertIn(str(audio_file), db.data["files"])
        entry = db.data["files"][str(audio_file)]
        self.assertEqual(entry["hash"], "test_hash")
        self.assertEqual(entry["outputs"]["transcription"], str(markdown_file))
        self.assertEqual(entry["outputs"]["summary"], str(summary_file))
        self.assertIn("processed_at", entry)
        mock_save.assert_called_once()

    def test_get_processed_info(self):
        """Test getting processed file information"""
        db = ProcessedFilesDatabase(self.db_path)
        test_file = Path("/test/file.mp3")
        test_info = {"hash": "test", "processed_at": "2024-01-01"}
        db.data["files"][str(test_file)] = test_info

        info = db.get_processed_info(test_file)
        self.assertEqual(info, test_info)

        # Test non-existent file
        self.assertIsNone(db.get_processed_info(Path("/test/nonexistent.mp3")))

    @patch("src.obsidian.database.ProcessedFilesDatabase.save")
    def test_remove_processed_file(self, mock_save):
        """Test removing a processed file"""
        db = ProcessedFilesDatabase(self.db_path)
        test_file = Path("/test/file.mp3")
        db.data["files"][str(test_file)] = {"hash": "test"}

        db.remove_processed_file(test_file)

        self.assertNotIn(str(test_file), db.data["files"])
        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
