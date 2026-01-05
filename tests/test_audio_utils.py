"""Tests for audio utility functions"""

import unittest
from pathlib import Path
from unittest.mock import patch

from src.audio.utils import is_audio_file, format_duration, get_file_size_mb
from src.constants import AUDIO_EXTENSIONS


class TestAudioUtils(unittest.TestCase):
    """Test cases for audio utility functions"""

    def test_is_audio_file_valid_extensions(self):
        """Test is_audio_file with valid extensions"""
        for ext in AUDIO_EXTENSIONS:
            path = Path(f"test{ext}")
            self.assertTrue(is_audio_file(path))
            # Test case insensitive
            path_upper = Path(f"test{ext.upper()}")
            self.assertTrue(is_audio_file(path_upper))

    def test_is_audio_file_invalid_extensions(self):
        """Test is_audio_file with invalid extensions"""
        invalid_extensions = [".txt", ".md", ".pdf", ".docx", ".png"]
        for ext in invalid_extensions:
            path = Path(f"test{ext}")
            self.assertFalse(is_audio_file(path))

    def test_format_duration_seconds_only(self):
        """Test format_duration with seconds only"""
        self.assertEqual(format_duration(30), "30秒")
        self.assertEqual(format_duration(59), "59秒")

    def test_format_duration_minutes(self):
        """Test format_duration with minutes"""
        self.assertEqual(format_duration(60), "1分0秒")
        self.assertEqual(format_duration(90), "1分30秒")
        self.assertEqual(format_duration(3599), "59分59秒")

    def test_format_duration_hours(self):
        """Test format_duration with hours"""
        self.assertEqual(format_duration(3600), "1時間0分0秒")
        self.assertEqual(format_duration(3661), "1時間1分1秒")
        self.assertEqual(format_duration(7200), "2時間0分0秒")

    @patch("src.audio.utils.Path.stat")
    def test_get_file_size_mb(self, mock_stat):
        """Test get_file_size_mb"""
        # Mock file size in bytes
        mock_stat.return_value.st_size = 1024 * 1024 * 5  # 5 MB
        path = Path("test.wav")
        size_mb = get_file_size_mb(path)
        self.assertEqual(size_mb, 5.0)

        # Test with fractional MB
        mock_stat.return_value.st_size = 1024 * 1024 * 2.5  # 2.5 MB
        size_mb = get_file_size_mb(path)
        self.assertEqual(size_mb, 2.5)


if __name__ == "__main__":
    unittest.main()
