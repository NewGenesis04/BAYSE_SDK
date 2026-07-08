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

        assert strategy.should_retry(0, 429) is True
        assert strategy.should_retry(1, 500) is True
        assert strategy.should_retry(2, 503) is True

    def test_should_not_retry_exhausted(self) -> None:
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(3, 429) is False

    def test_should_not_retry_non_retryable_status(self) -> None:
        config = RetryConfig(max_retries=3)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(0, 400) is False
        assert strategy.should_retry(0, 401) is False
        assert strategy.should_retry(0, 404) is False

    def test_jitter_is_applied(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=10.0, jitter=0.5)
        strategy = RetryStrategy(config)

        delay = strategy.delay(0)
        assert 1.0 <= delay <= 1.5

    def test_disabled_retries(self) -> None:
        config = RetryConfig(max_retries=0)
        strategy = RetryStrategy(config)

        assert strategy.should_retry(0, 429) is False
