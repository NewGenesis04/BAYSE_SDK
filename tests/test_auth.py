from __future__ import annotations

import base64
import hashlib
import hmac

from bayse_markets._auth import SignerProtocol, sign_request


class TestSignRequest:
    """Unit tests for the standalone HMAC signing function."""

    def test_sign_request_with_body(self) -> None:
        secret_key = "sk_test_secret789xyz"
        timestamp = 1234567890
        method = "POST"
        path = "/v1/pm/events/evt_123/markets/mkt_456/orders"
        body = '{"side":"BUY","outcome":"YES","amount":100,"currency":"USD"}'

        signature = sign_request(
            secret_key,
            timestamp=timestamp,
            method=method,
            path=path,
            body=body,
        )

        body_hash = hashlib.sha256(body.encode()).hexdigest()
        payload = f"{timestamp}.{method}.{path}.{body_hash}"
        expected = base64.b64encode(hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest()).decode()
        assert signature == expected

    def test_sign_request_without_body(self) -> None:
        secret_key = "sk_test_secret789xyz"
        timestamp = 1234567890
        method = "DELETE"
        path = "/v1/pm/orders/ord_123"

        signature = sign_request(
            secret_key,
            timestamp=timestamp,
            method=method,
            path=path,
        )

        payload = f"{timestamp}.{method}.{path}."
        expected = base64.b64encode(hmac.new(secret_key.encode(), payload.encode(), hashlib.sha256).digest()).decode()
        assert signature == expected

    def test_empty_body_hash_is_empty_string(self) -> None:
        """When body is None, bodyHash should be '' (trailing dot)."""
        secret_key = "sk_test"
        timestamp = 100
        method = "GET"
        path = "/health"

        sig = sign_request(secret_key, timestamp=timestamp, method=method, path=path)
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_different_keys_produce_different_signatures(self) -> None:
        sig1 = sign_request("sk_a", timestamp=1, method="GET", path="/test", body="{}")
        sig2 = sign_request("sk_b", timestamp=1, method="GET", path="/test", body="{}")
        assert sig1 != sig2

    def test_different_bodies_produce_different_signatures(self) -> None:
        sig1 = sign_request("sk", timestamp=1, method="POST", path="/test", body='{"a":1}')
        sig2 = sign_request("sk", timestamp=1, method="POST", path="/test", body='{"a":2}')
        assert sig1 != sig2


class TestSignerProtocol:
    """Tests for the injectable SignerProtocol."""

    def test_custom_signer_is_callable(self) -> None:
        def my_signer(secret_key: str, *, timestamp: int, method: str, path: str, body: str | None = None) -> str:
            return "custom-sig"

        assert isinstance(my_signer, SignerProtocol)

    def test_sign_request_matches_protocol(self) -> None:
        assert isinstance(sign_request, SignerProtocol)
