"""Obsidian note generation"""

from pathlib import Path
from datetime import datetime
from typing import Optional

from src.audio.utils import get_audio_duration, format_duration, get_file_size_mb
from src.constants import DEFAULT_TAGS, SUMMARY_TAGS, PROGRESS_TAGS
from src.utils.logging import get_logger

logger = get_logger(__name__)


class NoteGenerator:
    """Generator for Obsidian markdown notes"""

    def __init__(self, vault_path: Path):
        """
        Initialize note generator

        Args:
            vault_path: Path to the Obsidian vault
        """
        self.vault_path = vault_path

    def create_transcription_note(
        self, audio_path: Path, transcription: str, tags: Optional[list] = None
    ) -> str:
        """
        Create a transcription markdown note

        Args:
            audio_path: Path to the audio file
            transcription: Transcribed text
            tags: Optional custom tags

        Returns:
            Markdown content
        """
        logger.debug(f"Creating transcription note for: {audio_path}")

        # Get relative path from vault
        try:
            relative_path = audio_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = audio_path

        # Get file metadata
        try:
            duration = get_audio_duration(audio_path)
            duration_str = format_duration(duration)
            file_size_mb = get_file_size_mb(audio_path)
        except Exception as e:
            logger.warning(f"Failed to get file metadata: {e}")
            duration_str = "不明"
            file_size_mb = 0

        # Use default tags if not provided
        if tags is None:
            tags = DEFAULT_TAGS

        # Create markdown content
        markdown_content = f"""---
tags: {tags}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: {relative_path}
duration: {duration_str}
file_size: {file_size_mb:.2f} MB
---

# {audio_path.stem} - 文字起こし

## メタ情報
- **元ファイル**: [[{relative_path}]]
- **録音時間**: {duration_str}
- **ファイルサイズ**: {file_size_mb:.2f} MB
- **文字起こし日時**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 文字起こし内容

{transcription}

---
*このノートはGemini APIによって自動生成されました*
"""
        return markdown_content

    def create_summary_note(
        self,
        audio_path: Path,
        transcription: str,
        summary: str,
        tags: Optional[list] = None,
    ) -> str:
        """
        Create a summary markdown note

        Args:
            audio_path: Path to the audio file
            transcription: Original transcribed text
            summary: Summary text
            tags: Optional custom tags

        Returns:
            Markdown content
        """
        logger.debug(f"Creating summary note for: {audio_path}")

        # Get relative path from vault
        try:
            relative_path = audio_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = audio_path

        # Get file metadata
        try:
            duration = get_audio_duration(audio_path)
            duration_str = format_duration(duration)
        except Exception as e:
            logger.warning(f"Failed to get file metadata: {e}")
            duration_str = "不明"

        # Calculate character count
        char_count = len(transcription)

        # Use default tags if not provided
        if tags is None:
            tags = SUMMARY_TAGS

        # Create markdown content
        markdown_content = f"""---
tags: {tags}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: {relative_path}
duration: {duration_str}
transcription_length: {char_count}文字
---

# {audio_path.stem} - 要約

## メタ情報
- **元ファイル**: [[{relative_path}]]
- **文字起こし**: [[{audio_path.stem}_文字起こし]]
- **録音時間**: {duration_str}
- **文字数**: {char_count:,}文字
- **要約生成日時**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 要約

{summary}

---

## 関連ノート
- [[{audio_path.stem}_文字起こし|完全な文字起こしを見る]]

---
*このノートはGemini APIによって自動生成されました*
"""
        return markdown_content

    def save_note(self, content: str, file_path: Path) -> None:
        """
        Save markdown note to file

        Args:
            content: Markdown content
            file_path: Path to save the file
        """
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Save file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"Saved note: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save note: {e}")
            raise

    def get_progress_note_path(self, audio_path: Path) -> Path:
        """
        Get the path for a progress note

        Args:
            audio_path: Path to the audio file

        Returns:
            Path to the progress note
        """
        return audio_path.parent / f"{audio_path.stem}_処理中.md"

    def create_progress_note(
        self,
        audio_path: Path,
        status: str = "処理開始",
        details: Optional[str] = None,
        segment_info: Optional[tuple[int, int]] = None,
        tags: Optional[list] = None,
    ) -> str:
        """
        Create a progress markdown note

        Args:
            audio_path: Path to the audio file
            status: Current processing status
            details: Optional additional details
            segment_info: Optional tuple of (current_segment, total_segments)
            tags: Optional custom tags

        Returns:
            Markdown content
        """
        logger.debug(f"Creating progress note for: {audio_path}")

        # Get relative path from vault
        try:
            relative_path = audio_path.relative_to(self.vault_path)
        except ValueError:
            relative_path = audio_path

        # Get file metadata
        try:
            duration = get_audio_duration(audio_path)
            duration_str = format_duration(duration)
            file_size_mb = get_file_size_mb(audio_path)
        except Exception as e:
            logger.warning(f"Failed to get file metadata: {e}")
            duration_str = "不明"
            file_size_mb = 0

        # Use default tags if not provided
        if tags is None:
            tags = PROGRESS_TAGS

        # Build progress section
        progress_section = f"**現在のステータス**: {status}"
        if segment_info:
            current, total = segment_info
            progress_percent = (current / total) * 100
            progress_bar = self._create_progress_bar(current, total)
            progress_section += f"\n\n### セグメント処理\n- 進捗: {current}/{total} ({progress_percent:.0f}%)\n- {progress_bar}"

        if details:
            progress_section += f"\n\n### 詳細\n{details}"

        # Create markdown content
        markdown_content = f"""---
tags: {tags}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: {relative_path}
status: processing
---

# 🔄 {audio_path.stem} - 処理中

> ⚠️ このファイルは処理が完了すると自動的に削除されます

## 処理状況

{progress_section}

## ファイル情報
- **元ファイル**: [[{relative_path}]]
- **録音時間**: {duration_str}
- **ファイルサイズ**: {file_size_mb:.2f} MB
- **処理開始時刻**: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

---
*このノートはGemini APIによる処理中に自動生成されています*
"""
        return markdown_content

    def _create_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """
        Create a text-based progress bar

        Args:
            current: Current progress
            total: Total items
            width: Width of the progress bar

        Returns:
            Progress bar string
        """
        filled = int((current / total) * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"

    def update_progress_note(
        self,
        audio_path: Path,
        status: str,
        details: Optional[str] = None,
        segment_info: Optional[tuple[int, int]] = None,
    ) -> None:
        """
        Update an existing progress note

        Args:
            audio_path: Path to the audio file
            status: Current processing status
            details: Optional additional details
            segment_info: Optional tuple of (current_segment, total_segments)
        """
        progress_path = self.get_progress_note_path(audio_path)
        content = self.create_progress_note(audio_path, status, details, segment_info)
        self.save_note(content, progress_path)
        logger.debug(f"Updated progress note: {progress_path}")

    def delete_progress_note(self, audio_path: Path) -> None:
        """
        Delete a progress note

        Args:
            audio_path: Path to the audio file
        """
        progress_path = self.get_progress_note_path(audio_path)
        try:
            if progress_path.exists():
                progress_path.unlink()
                logger.info(f"Deleted progress note: {progress_path}")
        except Exception as e:
            logger.warning(f"Failed to delete progress note: {e}")
