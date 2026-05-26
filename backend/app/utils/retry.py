"""
Retry Mechanisms
================
Production-grade retry logic using tenacity.
Handles transient failures for OpenAI API calls, DB ops, and agent steps.
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, Tuple, Type

from tenacity import (
    AsyncRetrying,
    RetryError,
    Retrying,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_random_exponential,
)

logger = logging.getLogger("utils.retry")


# --- Exceptions that should trigger a retry ---
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)

try:
    import openai
    RETRYABLE_EXCEPTIONS = RETRYABLE_EXCEPTIONS + (
        openai.APIConnectionError,
        openai.APITimeoutError,
        openai.RateLimitError,
        openai.InternalServerError,
    )
except ImportError:
    pass


def with_retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    reraise: bool = True,
):
    """
    Decorator: synchronous retry with exponential backoff.

    Usage:
        @with_retry(max_attempts=3)
        def call_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in Retrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
                retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=reraise,
            ):
                with attempt:
                    return func(*args, **kwargs)
        return wrapper
    return decorator


def with_async_retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    reraise: bool = True,
):
    """
    Decorator: asynchronous retry with exponential backoff.

    Usage:
        @with_async_retry(max_attempts=3)
        async def call_openai():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(max_attempts),
                wait=wait_random_exponential(multiplier=1, min=wait_min, max=wait_max),
                retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=reraise,
            ):
                with attempt:
                    return await func(*args, **kwargs)
        return wrapper
    return decorator


async def retry_async_call(
    coro_func: Callable,
    *args,
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 8.0,
    **kwargs,
) -> Any:
    """
    Call an async function with retry logic.
    Useful when you can't use the decorator pattern.

    Args:
        coro_func: Async callable to execute
        *args: Positional arguments
        max_attempts: Maximum retry attempts
        wait_min: Minimum wait between retries (seconds)
        wait_max: Maximum wait between retries (seconds)
        **kwargs: Keyword arguments

    Returns:
        Result of coro_func(*args, **kwargs)

    Raises:
        Last exception after all retries exhausted
    """
    last_exception: Optional[Exception] = None

    for attempt_num in range(1, max_attempts + 1):
        try:
            return await coro_func(*args, **kwargs)
        except RETRYABLE_EXCEPTIONS as e:
            last_exception = e
            if attempt_num < max_attempts:
                wait_time = min(wait_min * (2 ** (attempt_num - 1)), wait_max)
                logger.warning(
                    f"Attempt {attempt_num}/{max_attempts} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"All {max_attempts} attempts failed. Last error: {e}"
                )
        except Exception as e:
            # Non-retryable exception — raise immediately
            logger.error(f"Non-retryable error in {coro_func.__name__}: {e}")
            raise

    raise last_exception


class CircuitBreaker:
    """
    Simple circuit breaker pattern for external service calls.
    Prevents cascading failures by stopping calls when error rate is high.

    States:
        CLOSED  → normal operation
        OPEN    → calls blocked, returns error immediately
        HALF    → test call allowed to see if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            elapsed = asyncio.get_event_loop().time() - (self._last_failure_time or 0)
            if elapsed >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                logger.info(f"CircuitBreaker '{self.name}': OPEN → HALF_OPEN")
        return self._state

    def record_success(self) -> None:
        self._failure_count = 0
        if self._state == self.HALF_OPEN:
            self._state = self.CLOSED
            logger.info(f"CircuitBreaker '{self.name}': HALF_OPEN → CLOSED")

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = asyncio.get_event_loop().time()
        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            logger.warning(
                f"CircuitBreaker '{self.name}': CLOSED → OPEN "
                f"(failures={self._failure_count})"
            )

    def is_allowed(self) -> bool:
        return self.state in (self.CLOSED, self.HALF_OPEN)
