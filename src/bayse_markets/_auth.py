from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Protocol, runtime_checkable


@runtime_checkable
class SignerProtocol(Protocol):
    """Protocol for injectable request signers.

    Implement this if you need custom signing logic (e.g. hardware-backed keys).
    """

    def __call__(self, secret_key: str, *, timestamp: int, method: str, path: str, body: str | None = None) -> str:
        """Return the base64-encoded HMAC-SHA256 signature."""
        ...


def sign_request(
    secret_key: str,
    *,
    timestamp: int,
    method: str,
    path: str,
    body: str | None = None,
) -> str:
    """Create an HMAC-SHA256 signature for a Bayse API request.

    The signing payload format is: ``{timestamp}.{METHOD}.{path}.{bodyHash}``

    Args:
        secret_key: The ``sk_*`` secret API key.
        timestamp: Current Unix timestamp (seconds since epoch).
        method: HTTP method in uppercase (e.g. ``POST``, ``DELETE``).
        path: Request path (e.g. ``/v1/pm/events/evt_123``).
        body: Raw JSON request body string, or ``None`` if no body.

    Returns:
        Base64-encoded HMAC-SHA256 signature string.
    """
    body_hash = ""
    if body:
        body_hash = hashlib.sha256(body.encode()).hexdigest()

    payload = f"{timestamp}.{method}.{path}.{body_hash}"

    digest = hmac.new(
        secret_key.encode(),
        payload.encode(),
        hashlib.sha256,
    ).digest()

    return base64.b64encode(digest).decode()
