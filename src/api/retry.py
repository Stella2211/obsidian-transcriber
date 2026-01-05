"""Retry logic for API calls"""

import time
import threading
from typing import Callable, TypeVar, Optional
from concurrent.futures import TimeoutError

from src.constants import (
    MAX_RETRIES,
    DEFAULT_TIMEOUT,
    RETRY_BACKOFF_BASE,
    MAX_RETRY_WAIT,
    RETRYABLE_ERROR_KEYWORDS,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryableError(Exception):
    """Exception that indicates an error that should trigger a retry"""

    pass


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable based on error message

    Args:
        error: The exception to check

    Returns:
        True if the error should trigger a retry
    """
    # RetryableError is always retryable
    if isinstance(error, RetryableError):
        return True

    error_msg = str(error).lower()
    return any(keyword in error_msg for keyword in RETRYABLE_ERROR_KEYWORDS)


def execute_with_timeout(func: Callable[[], T], timeout: int = DEFAULT_TIMEOUT) -> T:
    """
    Execute a function with a timeout

    Args:
        func: Function to execute
        timeout: Timeout in seconds

    Returns:
        Function result

    Raises:
        TimeoutError: If function execution exceeds timeout
        Exception: Any exception raised by the function
    """
    result: list[Optional[T]] = [None]
    exception: list[Optional[Exception]] = [None]

    def run_func():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e

    thread = threading.Thread(target=run_func)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        logger.warning(f"Function execution timed out after {timeout} seconds")
        raise TimeoutError(f"Function execution timed out after {timeout} seconds")

    if exception[0]:
        raise exception[0]

    return result[0]  # type: ignore


def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = MAX_RETRIES,
    timeout: int = DEFAULT_TIMEOUT,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    """
    Execute a function with retry logic and exponential backoff

    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        timeout: Timeout for each attempt in seconds
        on_retry: Optional callback called before each retry with (attempt_number, last_error)

    Returns:
        Function result

    Raises:
        Exception: The last exception if all retries are exhausted
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                # Calculate exponential backoff
                wait_time = min(
                    RETRY_BACKOFF_BASE * (2 ** (attempt - 1)), MAX_RETRY_WAIT
                )
                logger.info(
                    f"Retry {attempt}/{max_retries}: waiting {wait_time} seconds"
                )
                time.sleep(wait_time)

            if attempt > 0:
                logger.info(f"Retry {attempt}/{max_retries}: executing request")

            return execute_with_timeout(func, timeout)

        except TimeoutError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} timed out: {e}")
            if on_retry and attempt < max_retries - 1:
                on_retry(attempt + 1, e)
            continue

        except Exception as e:
            last_error = e

            if is_retryable_error(e):
                logger.warning(f"Retryable error on attempt {attempt + 1}: {e}")
                if on_retry and attempt < max_retries - 1:
                    on_retry(attempt + 1, e)
                continue
            else:
                logger.error(f"Non-retryable error: {e}")
                raise e

    # All retries exhausted
    error_msg = f"Maximum retries ({max_retries}) reached. Last error: {last_error}"
    logger.error(error_msg)
    raise Exception(error_msg)
