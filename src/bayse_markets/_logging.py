from __future__ import annotations

import logging

_LOGGER: logging.Logger | None = None


def get_logger() -> logging.Logger:
    """Return the SDK logger, creating it on first call."""
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = logging.getLogger("bayse_markets")
        _LOGGER.addHandler(logging.NullHandler())
    return _LOGGER


SENSITIVE_HEADERS = frozenset(
    {
        "x-auth-token",
        "authorization",
        "x-device-id",
        "x-signature",
        "x-public-key",
    }
)


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive values masked."""
    return {k: ("<redacted>" if k.lower() in SENSITIVE_HEADERS else v) for k, v in headers.items()}
