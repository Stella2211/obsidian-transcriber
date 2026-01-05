"""Tests for retry logic"""

import pytest

from src.api.retry import (
    parse_rate_limit_wait_time,
    is_rate_limit_error,
    is_retryable_error,
    RetryableError,
)


class TestParseRateLimitWaitTime:
    """Tests for parse_rate_limit_wait_time function"""

    def test_parse_minutes_and_seconds(self):
        """Test parsing '1m6s' format"""
        message = "Please try again in 1m6s. Need more tokens?"
        result = parse_rate_limit_wait_time(message)
        assert result == 66.0

    def test_parse_seconds_only(self):
        """Test parsing '30s' format"""
        message = "Please try again in 30s"
        result = parse_rate_limit_wait_time(message)
        assert result == 30.0

    def test_parse_minutes_only(self):
        """Test parsing '2m' format"""
        message = "Please try again in 2m"
        result = parse_rate_limit_wait_time(message)
        assert result == 120.0

    def test_parse_decimal_seconds(self):
        """Test parsing '1.5s' format"""
        message = "try again in 1.5s"
        result = parse_rate_limit_wait_time(message)
        assert result == 1.5

    def test_parse_real_groq_error(self):
        """Test parsing actual Groq error message"""
        message = (
            "Error code: 429 - {'error': {'message': 'Rate limit reached for model "
            "`whisper-large-v3-turbo` in organization `org_01kczw575cfawvmew13tng0c0e` "
            "service tier `on_demand` on secondsof audio per hour (ASPH): Limit 7200, "
            "Used 6107, Requested 1225. Please try again in 1m6s. Need more tokens? "
            "Upgrade to Dev Tier today at https://console.groq.com/settings/billing', "
            "'type': 'seconds', 'code': 'rate_limit_exceeded'}}"
        )
        result = parse_rate_limit_wait_time(message)
        assert result == 66.0

    def test_no_match(self):
        """Test when there's no wait time in the message"""
        message = "An error occurred"
        result = parse_rate_limit_wait_time(message)
        assert result is None

    def test_case_insensitive(self):
        """Test case insensitivity"""
        message = "Try Again In 5m30s"
        result = parse_rate_limit_wait_time(message)
        assert result == 330.0


class TestIsRateLimitError:
    """Tests for is_rate_limit_error function"""

    def test_429_error(self):
        """Test 429 status code detection"""
        error = Exception("Error code: 429 - rate limit")
        assert is_rate_limit_error(error) is True

    def test_rate_limit_keyword(self):
        """Test 'rate limit' keyword detection"""
        error = Exception("Rate limit exceeded")
        assert is_rate_limit_error(error) is True

    def test_rate_limit_underscore(self):
        """Test 'rate_limit' keyword detection"""
        error = Exception("rate_limit_exceeded")
        assert is_rate_limit_error(error) is True

    def test_not_rate_limit(self):
        """Test non-rate-limit error"""
        error = Exception("Server error 500")
        assert is_rate_limit_error(error) is False


class TestIsRetryableError:
    """Tests for is_retryable_error function"""

    def test_retryable_error_exception(self):
        """Test RetryableError is always retryable"""
        error = RetryableError("test error")
        assert is_retryable_error(error) is True

    def test_server_error(self):
        """Test server error is retryable"""
        error = Exception("server error occurred")
        assert is_retryable_error(error) is True

    def test_429_error(self):
        """Test 429 error is retryable"""
        error = Exception("Error 429: Too many requests")
        assert is_retryable_error(error) is True

    def test_non_retryable_error(self):
        """Test non-retryable error"""
        error = Exception("Invalid input")
        assert is_retryable_error(error) is False
