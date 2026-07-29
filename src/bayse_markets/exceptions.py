from __future__ import annotations

from datetime import datetime


class BayseError(Exception):
    """Base exception for all Bayse SDK errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int,
        response_headers: dict[str, str] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.response_headers = response_headers or {}
        self.timestamp = timestamp
        super().__init__(f"[{status_code}] {error_code}: {message}")


class InvalidSignatureError(BayseError):
    """The provided signature does not match the expected signature."""


class TimestampExpiredError(BayseError):
    """Request timestamp is too old (outside the 5-minute window)."""


class UnauthorizedError(BayseError):
    """API key is missing or invalid for the requested endpoint."""


class NotFoundError(BayseError):
    """The requested resource does not exist."""


class ValidationError(BayseError):
    """Request validation failed (422)."""


class RateLimitError(BayseError):
    """Rate limit exceeded. Carries retry-after info when available."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int,
        response_headers: dict[str, str] | None = None,
        timestamp: datetime | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(error_code, message, status_code, response_headers, timestamp)


class InternalServerError(BayseError):
    """Server-side error (500)."""


class NetworkError(BayseError):
    """Transport-level error (connection timeout, DNS failure, SSL error, etc.).

    Attributes:
        original_exception: The underlying ``httpx`` exception, class preserved.
        request_sent: Whether the request reached the server.

            * ``False`` — the connection was never established, so the server
              definitively never saw it. A write that fails this way is cleanly
              rejected and can be re-sent without risk of duplication.
            * ``None`` — unknown. The connection was up when it failed, so the
              request may well have been received and processed. Callers must treat
              a failed write as an unresolved state.
            * ``True`` — reserved; the SDK never claims certainty here today.
    """

    def __init__(
        self,
        message: str,
        original_exception: Exception | None = None,
        request_sent: bool | None = None,
    ) -> None:
        self.original_exception = original_exception
        self.request_sent = request_sent
        super().__init__(
            error_code="network_error",
            message=message,
            status_code=0,
        )


def classify_request_sent(exc: Exception) -> bool | None:
    """Classify whether a transport exception left the machine.

    Returns ``False`` only for connect-phase failures, where no bytes of the request
    ever reached the server. Everything else returns ``None`` — once the connection is
    established, a read failure cannot distinguish "never processed" from "processed,
    response lost".
    """
    import httpx

    never_sent = (
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.PoolTimeout,
        httpx.ProxyError,
        httpx.UnsupportedProtocol,
        httpx.InvalidURL,
    )
    if isinstance(exc, never_sent):
        return False
    return None


_ERROR_CODE_MAP: dict[str, type[BayseError]] = {
    "invalid_signature": InvalidSignatureError,
    "timestamp_expired": TimestampExpiredError,
    "unauthorized": UnauthorizedError,
    "not_found": NotFoundError,
    "validation_error": ValidationError,
    "rate_limit": RateLimitError,
    "internal_server_error": InternalServerError,
}


def error_from_response(
    error_code: str,
    message: str,
    status_code: int,
    response_headers: dict[str, str] | None = None,
    timestamp: datetime | None = None,
) -> BayseError:
    """Factory: maps an API error code string to the correct exception class."""
    exc_cls = _ERROR_CODE_MAP.get(error_code, BayseError)
    if exc_cls is RateLimitError:
        retry_after = _parse_retry_after(response_headers)
        return RateLimitError(
            error_code=error_code,
            message=message,
            status_code=status_code,
            response_headers=response_headers,
            timestamp=timestamp,
            retry_after_seconds=retry_after,
        )
    return exc_cls(
        error_code=error_code,
        message=message,
        status_code=status_code,
        response_headers=response_headers,
        timestamp=timestamp,
    )


def _parse_retry_after(headers: dict[str, str] | None) -> float | None:
    if not headers:
        return None
    raw = headers.get("Retry-After") or headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None
