"""Tests for configuration management"""

import unittest
import os
from pathlib import Path
from unittest.mock import patch
from argparse import Namespace

from src.config import Config


class TestConfig(unittest.TestCase):
    """Test cases for Config class"""

    @patch.dict(
        os.environ,
        {"GROQ_API_KEY": "test_groq_key", "GEMINI_API_KEY": "test_gemini_key"},
    )
    def test_from_env(self):
        """Test Config.from_env method"""
        config = Config.from_env()
        self.assertEqual(config.groq_api_key, "test_groq_key")
        self.assertEqual(config.gemini_api_key, "test_gemini_key")
        self.assertIsNone(config.watch_folder)
        self.assertIsNone(config.db_path)
        self.assertTrue(config.create_summary)
        self.assertFalse(config.verbose)
        self.assertEqual(config.chunk_overlap_seconds, 10)

    @patch.dict(os.environ, {}, clear=True)
    def test_from_env_no_groq_api_key(self):
        """Test Config.from_env without Groq API key"""
        with self.assertRaises(ValueError) as context:
            Config.from_env()
        self.assertIn("Groq API key not found", str(context.exception))

    @patch.dict(os.environ, {"GROQ_API_KEY": "test_groq_key"}, clear=True)
    def test_from_env_no_gemini_api_key(self):
        """Test Config.from_env without Gemini API key"""
        with self.assertRaises(ValueError) as context:
            Config.from_env()
        self.assertIn("Gemini API key not found", str(context.exception))

    @patch.dict(
        os.environ, {"GROQ_API_KEY": "env_groq_key", "GEMINI_API_KEY": "env_gemini_key"}
    )
    def test_from_args_with_env(self):
        """Test Config.from_args with environment variable"""
        args = Namespace(
            groq_api_key=None,
            gemini_api_key=None,
            watch_folder="/test/vault",
            db_path=None,
            verbose=True,
            no_summary=False,
            scan_existing=True,
            chunk_overlap=None,
            env_file=".env",
        )
        config = Config.from_args(args)
        self.assertEqual(config.groq_api_key, "env_groq_key")
        self.assertEqual(config.gemini_api_key, "env_gemini_key")
        self.assertEqual(config.watch_folder, Path("/test/vault"))
        self.assertTrue(config.verbose)
        self.assertTrue(config.create_summary)
        self.assertTrue(config.scan_existing)
        self.assertEqual(config.chunk_overlap_seconds, 10)  # default

    def test_from_args_with_api_keys(self):
        """Test Config.from_args with explicit API keys"""
        args = Namespace(
            groq_api_key="explicit_groq_key",
            gemini_api_key="explicit_gemini_key",
            watch_folder="/test/vault",
            db_path="/test/db.json",
            verbose=False,
            no_summary=True,
            scan_existing=False,
            chunk_overlap=15,
            env_file=None,
        )
        config = Config.from_args(args)
        self.assertEqual(config.groq_api_key, "explicit_groq_key")
        self.assertEqual(config.gemini_api_key, "explicit_gemini_key")
        self.assertEqual(config.db_path, Path("/test/db.json"))
        self.assertFalse(config.create_summary)
        self.assertFalse(config.scan_existing)
        self.assertEqual(config.chunk_overlap_seconds, 15)

    def test_get_db_path_explicit(self):
        """Test get_db_path with explicit path"""
        config = Config(
            groq_api_key="test",
            gemini_api_key="test",
            db_path=Path("/explicit/db.json"),
        )
        self.assertEqual(config.get_db_path(), Path("/explicit/db.json"))

    @patch("src.config.Path.exists")
    def test_get_db_path_obsidian_folder(self, mock_exists):
        """Test get_db_path with .obsidian folder"""
        mock_exists.return_value = True
        config = Config(
            groq_api_key="test", gemini_api_key="test", watch_folder=Path("/vault")
        )
        expected = Path("/vault/.obsidian/.transcription_db.json")
        self.assertEqual(config.get_db_path(), expected)

    @patch("src.config.Path.exists")
    def test_get_db_path_no_obsidian_folder(self, mock_exists):
        """Test get_db_path without .obsidian folder"""
        mock_exists.return_value = False
        config = Config(
            groq_api_key="test", gemini_api_key="test", watch_folder=Path("/vault")
        )
        expected = Path("/vault/.transcription_db.json")
        self.assertEqual(config.get_db_path(), expected)

    def test_get_db_path_default(self):
        """Test get_db_path with no watch folder"""
        config = Config(groq_api_key="test", gemini_api_key="test")
        self.assertEqual(config.get_db_path(), Path(".transcription_db.json"))


if __name__ == "__main__":
    unittest.main()
