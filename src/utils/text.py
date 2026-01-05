"""Text processing utilities for transcription deduplication"""

from typing import Tuple, Optional
from src.utils.logging import get_logger

logger = get_logger(__name__)


def find_overlap(text_a: str, text_b: str, min_overlap: int = 10, max_overlap: int = 200) -> Optional[str]:
    """
    Find overlapping text between the end of text_a and the beginning of text_b.

    This function searches for the longest common substring where text_a ends
    and text_b begins. This is useful for merging transcription segments that
    have overlapping audio.

    Args:
        text_a: First text (we look at its ending)
        text_b: Second text (we look at its beginning)
        min_overlap: Minimum characters to consider as valid overlap
        max_overlap: Maximum characters to search for overlap

    Returns:
        The overlapping string if found, None otherwise
    """
    if not text_a or not text_b:
        return None

    # Limit search range for efficiency
    search_end = text_a[-max_overlap:] if len(text_a) > max_overlap else text_a
    search_start = text_b[:max_overlap] if len(text_b) > max_overlap else text_b

    # Try to find the longest overlap
    # Start from the longest possible and work down
    max_possible = min(len(search_end), len(search_start))

    for length in range(max_possible, min_overlap - 1, -1):
        # Get the end of text_a
        end_of_a = search_end[-length:]
        # Get the start of text_b
        start_of_b = search_start[:length]

        if end_of_a == start_of_b:
            return end_of_a

    return None


def merge_segments_with_dedup(
    segment_a: str,
    segment_b: str,
    min_overlap: int = 10,
    max_overlap: int = 200,
) -> Tuple[str, bool]:
    """
    Merge two text segments, removing duplicate content at the boundary.

    If an exact overlap is found, it removes the duplicate. If no overlap
    is found (possibly due to transcription differences like kanji/hiragana),
    both segments are kept with a separator.

    Args:
        segment_a: First segment text
        segment_b: Second segment text
        min_overlap: Minimum characters to consider as valid overlap
        max_overlap: Maximum characters to search for overlap

    Returns:
        Tuple of (merged_text, dedup_success)
        - merged_text: The combined text
        - dedup_success: True if deduplication was performed, False if both kept
    """
    # Clean up whitespace
    segment_a = segment_a.strip()
    segment_b = segment_b.strip()

    if not segment_a:
        return segment_b, True
    if not segment_b:
        return segment_a, True

    # Try to find overlap
    overlap = find_overlap(segment_a, segment_b, min_overlap, max_overlap)

    if overlap:
        # Remove the overlapping part from segment_b
        merged = segment_a + segment_b[len(overlap):]
        logger.debug(f"Found overlap of {len(overlap)} chars: '{overlap[:50]}...'")
        return merged, True
    else:
        # No overlap found - keep both with separator
        # This handles cases where transcription differs (kanji vs hiragana, etc.)
        merged = segment_a + "\n\n" + segment_b
        logger.debug("No overlap found, keeping both segments")
        return merged, False


def merge_all_segments(
    segments: list[str],
    min_overlap: int = 10,
    max_overlap: int = 200,
) -> Tuple[str, int, int]:
    """
    Merge multiple text segments, removing duplicates at boundaries.

    Args:
        segments: List of text segments to merge
        min_overlap: Minimum characters to consider as valid overlap
        max_overlap: Maximum characters to search for overlap

    Returns:
        Tuple of (merged_text, successful_dedup_count, failed_dedup_count)
    """
    if not segments:
        return "", 0, 0

    if len(segments) == 1:
        return segments[0].strip(), 0, 0

    result = segments[0].strip()
    success_count = 0
    fail_count = 0

    for i in range(1, len(segments)):
        segment = segments[i].strip()
        if not segment:
            continue

        result, success = merge_segments_with_dedup(
            result, segment, min_overlap, max_overlap
        )

        if success:
            success_count += 1
        else:
            fail_count += 1
            logger.info(
                f"Segment {i}/{len(segments)-1}: No overlap found, "
                "both versions kept (possible kanji/hiragana difference)"
            )

    return result, success_count, fail_count
