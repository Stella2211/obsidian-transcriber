"""Tests for text deduplication utilities"""

import unittest

from src.utils.text import find_overlap, merge_segments_with_dedup, merge_all_segments


class TestFindOverlap(unittest.TestCase):
    """Test cases for find_overlap function"""

    def test_exact_overlap(self):
        """Test finding exact overlap between segments"""
        text_a = "こんにちは。今日は"
        text_b = "今日はいい天気ですね"
        overlap = find_overlap(text_a, text_b, min_overlap=3)
        self.assertEqual(overlap, "今日は")

    def test_longer_overlap(self):
        """Test finding longer overlap"""
        text_a = "これは長いテキストの例です。最後の部分が重複しています。"
        text_b = "最後の部分が重複しています。そして続きがあります。"
        overlap = find_overlap(text_a, text_b, min_overlap=5)
        self.assertEqual(overlap, "最後の部分が重複しています。")

    def test_no_overlap(self):
        """Test when there is no overlap"""
        text_a = "これは最初のテキストです。"
        text_b = "これは別のテキストです。"
        overlap = find_overlap(text_a, text_b, min_overlap=5)
        self.assertIsNone(overlap)

    def test_overlap_too_short(self):
        """Test when overlap is shorter than minimum"""
        text_a = "ABCこれ"
        text_b = "これDEF"
        overlap = find_overlap(text_a, text_b, min_overlap=5)
        self.assertIsNone(overlap)

    def test_empty_text(self):
        """Test with empty text"""
        self.assertIsNone(find_overlap("", "text", min_overlap=3))
        self.assertIsNone(find_overlap("text", "", min_overlap=3))
        self.assertIsNone(find_overlap("", "", min_overlap=3))


class TestMergeSegmentsWithDedup(unittest.TestCase):
    """Test cases for merge_segments_with_dedup function"""

    def test_merge_with_overlap(self):
        """Test merging segments with overlapping text"""
        segment_a = "こんにちは。今日は"
        segment_b = "今日はいい天気ですね"
        merged, success = merge_segments_with_dedup(segment_a, segment_b, min_overlap=3)
        self.assertTrue(success)
        self.assertEqual(merged, "こんにちは。今日はいい天気ですね")

    def test_merge_without_overlap(self):
        """Test merging segments without overlap (keeps both)"""
        segment_a = "最初のセグメント。"
        segment_b = "別のセグメント。"
        merged, success = merge_segments_with_dedup(segment_a, segment_b, min_overlap=5)
        self.assertFalse(success)
        self.assertIn("最初のセグメント。", merged)
        self.assertIn("別のセグメント。", merged)

    def test_merge_with_empty_segment(self):
        """Test merging with empty segment"""
        merged, success = merge_segments_with_dedup("テキスト", "", min_overlap=3)
        self.assertTrue(success)
        self.assertEqual(merged, "テキスト")

        merged, success = merge_segments_with_dedup("", "テキスト", min_overlap=3)
        self.assertTrue(success)
        self.assertEqual(merged, "テキスト")

    def test_whitespace_handling(self):
        """Test that whitespace is properly trimmed"""
        segment_a = "  テキストA  "
        segment_b = "  テキストB  "
        merged, success = merge_segments_with_dedup(segment_a, segment_b, min_overlap=3)
        self.assertFalse(merged.startswith(" "))
        self.assertFalse(merged.endswith(" "))


class TestMergeAllSegments(unittest.TestCase):
    """Test cases for merge_all_segments function"""

    def test_merge_multiple_segments(self):
        """Test merging multiple segments"""
        segments = [
            "これは最初のセグメントです。次に続く",
            "次に続くのは二番目です。最後に",
            "最後に三番目のセグメントです。"
        ]
        merged, success, fail = merge_all_segments(segments, min_overlap=3)
        self.assertEqual(success, 2)
        self.assertEqual(fail, 0)
        self.assertIn("最初のセグメント", merged)
        self.assertIn("三番目のセグメント", merged)

    def test_empty_list(self):
        """Test with empty list"""
        merged, success, fail = merge_all_segments([])
        self.assertEqual(merged, "")
        self.assertEqual(success, 0)
        self.assertEqual(fail, 0)

    def test_single_segment(self):
        """Test with single segment"""
        merged, success, fail = merge_all_segments(["単一のセグメント"])
        self.assertEqual(merged, "単一のセグメント")
        self.assertEqual(success, 0)
        self.assertEqual(fail, 0)

    def test_mixed_success_and_failure(self):
        """Test with some overlaps found and some not"""
        segments = [
            "セグメントA。重複部分",
            "重複部分はここ。",  # Has overlap
            "全く別のテキスト。"  # No overlap
        ]
        merged, success, fail = merge_all_segments(segments, min_overlap=3)
        self.assertEqual(success, 1)
        self.assertEqual(fail, 1)


if __name__ == "__main__":
    unittest.main()
