from __future__ import annotations

import random
import time as time_module

from bayse_markets._config import RetryConfig


class RetryStrategy:
    """Fixed-jitter exponential backoff strategy.

    Delay formula::

        delay = min(base_delay * 2^attempt, max_delay) + random(0, jitter)
    """

    def __init__(self, config: RetryConfig) -> None:
        self.config = config

    def delay(self, attempt: int) -> float:
        """Compute the delay in seconds for the given attempt number (0-indexed)."""
        exponential = self.config.base_delay * (2**attempt)
        capped = min(exponential, self.config.max_delay)
        jitter = random.random() * self.config.jitter
        return capped + jitter

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """Determine whether a retry should be attempted."""
        if attempt >= self.config.max_retries:
            return False
        return status_code in self.config.retry_on_statuses

    def sleep(self, attempt: int) -> None:
        """Blocking sleep. Used in synchronous contexts (rare).

        For the async client, ``asyncio.sleep`` is used directly instead.
        """
        time_module.sleep(self.delay(attempt))
