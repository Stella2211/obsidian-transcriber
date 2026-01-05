"""Application constants and configuration defaults"""

from typing import Set

# Audio file extensions
AUDIO_EXTENSIONS: Set[str] = {
    ".mp3",
    ".m4a",
    ".wav",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".webm",
    ".wma",
}

# API settings - Gemini (for summarization)
SUMMARY_MODEL = "gemini-flash-latest"  # Model for text summarization
MAX_RETRIES = 5
DEFAULT_TIMEOUT = 600  # 10 minutes
RETRY_BACKOFF_BASE = 10  # Base seconds for exponential backoff
MAX_RETRY_WAIT = 120  # Maximum wait between retries

# API settings - Groq Whisper (for transcription)
GROQ_TRANSCRIPTION_MODEL = "whisper-large-v3-turbo"
GROQ_TIMEOUT = 300  # 5 minutes per chunk

# Audio chunking settings (for files > 25MB)
MAX_CHUNK_SIZE_MB = 24  # Leave margin from 25MB limit
DEFAULT_CHUNK_OVERLAP_SECONDS = 10  # Overlap between chunks

# Server error keywords for retry logic
RETRYABLE_ERROR_KEYWORDS = [
    "server",
    "service",
    "unavailable",
    "503",
    "500",
    "429",
    "rate limit",
    "quota",
    "empty response",  # Added for None responses
    "no text content",  # Added for None responses
]

# File size limits
MAX_TRANSCRIPTION_PREVIEW_LENGTH = 15000  # Characters for summary generation

# Obsidian note settings
DEFAULT_TAGS = ["音声文字起こし", "自動生成"]
SUMMARY_TAGS = ["音声要約", "自動生成"]
PROGRESS_TAGS = ["処理中", "自動生成"]
