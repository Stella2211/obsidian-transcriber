"""Configuration management for the application"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration"""

    groq_api_key: str
    gemini_api_key: str
    watch_folder: Optional[Path] = None
    db_path: Optional[Path] = None
    create_summary: bool = True
    verbose: bool = False
    scan_existing: bool = False
    chunk_overlap_seconds: int = 10
    env_file: Path = Path(".env")
    hooks_config_path: Optional[Path] = None

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables"""
        if env_file:
            load_dotenv(env_file)

        groq_api_key = os.environ.get("GROQ_API_KEY", "")
        if not groq_api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or use --groq-api-key option"
            )

        gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        if not gemini_api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable "
                "or use --gemini-api-key option"
            )

        return cls(groq_api_key=groq_api_key, gemini_api_key=gemini_api_key)

    @classmethod
    def from_args(cls, args) -> "Config":
        """Create configuration from command line arguments"""
        # Load environment file if specified
        if (
            hasattr(args, "env_file")
            and args.env_file
            and os.path.exists(args.env_file)
        ):
            load_dotenv(args.env_file)

        # Get Groq API key from args or environment
        groq_api_key = getattr(args, "groq_api_key", None) or os.environ.get(
            "GROQ_API_KEY"
        )
        if not groq_api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable "
                "or use --groq-api-key option"
            )

        # Get Gemini API key from args or environment
        gemini_api_key = getattr(args, "gemini_api_key", None) or os.environ.get(
            "GEMINI_API_KEY"
        )
        if not gemini_api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable "
                "or use --gemini-api-key option"
            )

        config = cls(groq_api_key=groq_api_key, gemini_api_key=gemini_api_key)

        # Set optional attributes
        if hasattr(args, "watch_folder"):
            config.watch_folder = Path(args.watch_folder)
        if hasattr(args, "db_path") and args.db_path:
            config.db_path = Path(args.db_path)
        if hasattr(args, "verbose"):
            config.verbose = args.verbose
        if hasattr(args, "no_summary"):
            config.create_summary = not args.no_summary
        if hasattr(args, "scan_existing"):
            config.scan_existing = args.scan_existing
        if hasattr(args, "chunk_overlap") and args.chunk_overlap is not None:
            config.chunk_overlap_seconds = args.chunk_overlap
        if hasattr(args, "hooks_config") and args.hooks_config:
            config.hooks_config_path = Path(args.hooks_config)

        return config

    def get_hooks_config_path(self) -> Optional[Path]:
        """Get the hooks config path, checking default locations if not specified"""
        if self.hooks_config_path:
            return self.hooks_config_path

        # Check default locations
        default_paths = [
            Path("hooks.yaml"),
            Path("hooks.yml"),
        ]

        if self.watch_folder:
            default_paths.extend([
                self.watch_folder / "hooks.yaml",
                self.watch_folder / "hooks.yml",
                self.watch_folder / ".obsidian" / "hooks.yaml",
                self.watch_folder / ".obsidian" / "hooks.yml",
            ])

        for path in default_paths:
            if path.exists():
                return path

        return None

    def get_db_path(self) -> Path:
        """Get the database path, using default if not specified"""
        if self.db_path:
            return self.db_path

        if self.watch_folder:
            obsidian_folder = self.watch_folder / ".obsidian"
            if obsidian_folder.exists():
                return obsidian_folder / ".transcription_db.json"
            return self.watch_folder / ".transcription_db.json"

        return Path(".transcription_db.json")
