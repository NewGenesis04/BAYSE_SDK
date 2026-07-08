from __future__ import annotations

from bayse_markets.exceptions import (
    BayseError,
    InvalidSignatureError,
    NetworkError,
    RateLimitError,
    TimestampExpiredError,
    error_from_response,
)


class TestErrorFactory:
    """Tests for mapping error codes to exception classes."""

    def test_invalid_signature(self) -> None:
        exc = error_from_response(
            error_code="invalid_signature",
            message="Signature does not match",
            status_code=401,
        )
        assert isinstance(exc, InvalidSignatureError)
        assert exc.error_code == "invalid_signature"

    def test_timestamp_expired(self) -> None:
        exc = error_from_response(
            error_code="timestamp_expired",
            message="Timestamp is too old",
            status_code=401,
        )
        assert isinstance(exc, TimestampExpiredError)

    def test_rate_limit(self) -> None:
        exc = error_from_response(
            error_code="rate_limit",
            message="Too many requests",
            status_code=429,
            response_headers={"Retry-After": "30"},
        )
        assert isinstance(exc, RateLimitError)
        assert exc.retry_after_seconds == 30.0

    def test_unknown_error_code_falls_back_to_base(self) -> None:
        exc = error_from_response(
            error_code="some_unknown_code",
            message="Something happened",
            status_code=500,
        )
        assert isinstance(exc, BayseError)
        assert not isinstance(exc, InvalidSignatureError)

    def test_error_message_format(self) -> None:
        exc = error_from_response(
            error_code="unauthorized",
            message="Missing API key",
            status_code=401,
        )
        assert "401" in str(exc)
        assert "unauthorized" in str(exc)
        assert "Missing API key" in str(exc)


class TestNetworkError:
    """Tests for transport-level errors."""

    def test_wraps_original_exception(self) -> None:
        original = TimeoutError("connection timed out")
        exc = NetworkError(message="Request failed", original_exception=original)
        assert exc.original_exception is original
        assert exc.status_code == 0
        assert exc.error_code == "network_error"

    def test_no_original(self) -> None:
        exc = NetworkError(message="DNS resolution failed")
        assert exc.original_exception is None


class TestRateLimitParsing:
    """Tests for Retry-After header parsing."""

    def test_retry_after_from_headers(self) -> None:
        exc = error_from_response(
            error_code="rate_limit",
            message="Slow down",
            status_code=429,
            response_headers={"retry-after": "12.5"},
        )
        assert isinstance(exc, RateLimitError)
        assert exc.retry_after_seconds == 12.5

    def test_no_retry_after(self) -> None:
        exc = error_from_response(
            error_code="rate_limit",
            message="Slow down",
            status_code=429,
        )
        assert isinstance(exc, RateLimitError)
        assert exc.retry_after_seconds is None
