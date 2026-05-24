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
GROQ_TRANSCRIPTION_MODEL = "whisper-large-v3"
GROQ_TIMEOUT = 300  # 5 minutes per chunk
DEFAULT_TRANSCRIPTION_LANGUAGE = None  # None = Whisper が言語を自動判定

# Audio chunking settings (for files > 25MB)
MAX_CHUNK_SIZE_MB = 20  # Leave margin from 25MB limit
DEFAULT_CHUNK_OVERLAP_SECONDS = 10  # Overlap between chunks

# Chunk export format
# Groq downsamples audio to 16kHz mono internally before transcribing, so
# exporting chunks at 16kHz mono is lossless for ASR while keeping size small.
# Chunk duration is derived from this bitrate to guarantee each exported chunk
# stays under MAX_CHUNK_SIZE_MB regardless of the source file's bitrate.
CHUNK_SAMPLE_RATE = 16000  # 16kHz, Whisper's native sample rate
CHUNK_CHANNELS = 1  # Mono
CHUNK_BITRATE_KBPS = 64  # MP3 bitrate for exported chunks

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
