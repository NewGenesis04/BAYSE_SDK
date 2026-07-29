from __future__ import annotations

from bayse_markets._config import RetryConfig
from bayse_markets._retry import RetryStrategy


class TestRetryStrategy:
    """Unit tests for the fixed-jitter exponential backoff strategy."""

    def test_delay_increases_with_attempts(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=60.0, jitter=0.0)
        strategy = RetryStrategy(config)

        delays = [strategy.delay(i) for i in range(5)]
        for i in range(1, len(delays)):
            assert delays[i] >= delays[i - 1], f"Delay regressed at attempt {i}"

    def test_delay_is_capped_at_max(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=0.0, max_retries=10)
        strategy = RetryStrategy(config)

        delay = strategy.delay(10)
        assert delay <= 5.0

    def test_exponential_formula(self) -> None:
        config = RetryConfig(base_delay=2.0, max_delay=100.0, jitter=0.0)
        strategy = RetryStrategy(config)

        assert strategy.delay(0) == 2.0  # 2^0 * 2 = 2
        assert strategy.delay(1) == 4.0  # 2^1 * 2 = 4
        assert strategy.delay(2) == 8.0  # 2^2 * 2 = 8

    def test_should_retry_within_limit(self) -> None:
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(0, 429, method="GET") is True
        assert strategy.should_retry(1, 500, method="GET") is True
        assert strategy.should_retry(2, 503, method="GET") is True

    def test_should_not_retry_exhausted(self) -> None:
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(3, 429, method="GET") is False

    def test_should_not_retry_non_retryable_status(self) -> None:
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(0, 400, method="GET") is False
        assert strategy.should_retry(0, 401, method="GET") is False
        assert strategy.should_retry(0, 404, method="GET") is False

    def test_jitter_is_applied(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=10.0, jitter=0.5)
        strategy = RetryStrategy(config)

        delay = strategy.delay(0)
        assert 1.0 <= delay <= 1.5

    def test_disabled_retries(self) -> None:
        config = RetryConfig(max_retries=0)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(0, 429, method="GET") is False


class TestMethodAwareRetry:
    """A 5xx means different things on a GET and on a POST /orders."""

    def test_post_is_not_retried_on_5xx(self) -> None:
        """The core guarantee: a 502 on a POST may have been processed upstream."""
        strategy = RetryStrategy(RetryConfig(max_retries=3))

        for status in (500, 502, 503, 504):
            assert strategy.should_retry(0, status, method="POST") is False

    def test_post_is_not_retried_on_429_by_default(self) -> None:
        """Retrying a 429 assumes the limiter sits in front of order acceptance.

        That is unverifiable from the client, and if it is wrong the cost is
        ``max_retries + 1`` live orders. Opt in, never default.
        """
        strategy = RetryStrategy(RetryConfig(max_retries=3))

        assert strategy.should_retry(0, 429, method="POST") is False

    def test_no_status_at_all_retries_an_unsafe_request_by_default(self) -> None:
        strategy = RetryStrategy(RetryConfig(max_retries=3))

        for status in (429, 500, 502, 503, 504):
            assert strategy.should_retry(0, status, method="POST") is False

    def test_unsafe_statuses_are_configurable(self) -> None:
        """A caller who knows where their limiter sits can opt back in."""
        strategy = RetryStrategy(RetryConfig(max_retries=3, retry_unsafe_on_statuses=(429,)))

        assert strategy.should_retry(0, 429, method="POST") is True
        assert strategy.should_retry(0, 502, method="POST") is False

    def test_idempotency_key_reenables_5xx_retry_on_post(self) -> None:
        strategy = RetryStrategy(RetryConfig(max_retries=3))

        assert strategy.should_retry(0, 502, method="POST", idempotent=True) is True

    def test_delete_is_idempotent_by_specification(self) -> None:
        strategy = RetryStrategy(RetryConfig(max_retries=3))

        assert strategy.should_retry(0, 502, method="DELETE") is True

    def test_method_is_case_insensitive(self) -> None:
        strategy = RetryStrategy(RetryConfig(max_retries=3))

        assert strategy.should_retry(0, 502, method="get") is True
        assert strategy.should_retry(0, 502, method="post") is False

    def test_exhaustion_beats_idempotency(self) -> None:
        strategy = RetryStrategy(RetryConfig(max_retries=2))

        assert strategy.should_retry(2, 502, method="GET", idempotent=True) is False

    def test_unsafe_retry_still_respects_max_retries(self) -> None:
        strategy = RetryStrategy(
            RetryConfig(max_retries=2, retry_unsafe_on_statuses=(429,))
        )

        assert strategy.should_retry(1, 429, method="POST") is True
        assert strategy.should_retry(2, 429, method="POST") is False
