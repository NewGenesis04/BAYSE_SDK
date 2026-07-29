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

    def is_idempotent(self, method: str, *, idempotent: bool = False) -> bool:
        """Whether replaying a ``method`` request is safe.

        ``idempotent=True`` is how a caller declares safety the method itself cannot
        express — most importantly, that an ``Idempotency-Key`` header was sent.
        """
        if idempotent:
            return True
        normalized = method.upper()
        return (
            normalized in self.config.safe_methods
            or normalized in self.config.idempotent_methods
        )

    def should_retry(
        self,
        attempt: int,
        status_code: int,
        *,
        method: str,
        idempotent: bool = False,
    ) -> bool:
        """Determine whether a retry should be attempted.

        Non-idempotent requests (``POST`` without an idempotency key) are held to the
        narrower :attr:`~bayse_markets._config.RetryConfig.retry_unsafe_on_statuses`
        set, because a ``5xx`` on a write may mean the server processed it and lost
        the response.

        Args:
            attempt: Zero-indexed attempt number already made.
            status_code: HTTP status of the response being judged.
            method: HTTP method of the request. Required — the same status means
                different things on a ``GET`` and on a ``POST /orders``.
            idempotent: ``True`` when replaying is safe despite the method, e.g. an
                ``Idempotency-Key`` was sent.
        """
        if attempt >= self.config.max_retries:
            return False
        if self.is_idempotent(method, idempotent=idempotent):
            return status_code in self.config.retry_on_statuses
        return status_code in self.config.retry_unsafe_on_statuses

    def sleep(self, attempt: int) -> None:
        """Blocking sleep. Used in synchronous contexts (rare).

        For the async client, ``asyncio.sleep`` is used directly instead.
        """
        time_module.sleep(self.delay(attempt))
