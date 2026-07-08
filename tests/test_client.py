from __future__ import annotations

import pytest

from bayse_markets._client import BayseClient
from bayse_markets._config import Env, TraceConfig


class TestClientInit:
    """Tests for client initialisation and environment mapping."""

    def test_init_with_str_env(self) -> None:
        client = BayseClient("pk_test", "sk_test", env="production")
        assert client._env == Env.PRODUCTION

    def test_init_with_enum_env(self) -> None:
        client = BayseClient("pk_test", "sk_test", env=Env.SANDBOX)
        assert client._env == Env.SANDBOX

    def test_init_invalid_env_raises(self) -> None:
        with pytest.raises(ValueError, match="'invalid'"):
            BayseClient("pk_test", "sk_test", env="invalid")

    def test_trace_id_generation(self) -> None:
        client = BayseClient("pk_test", "sk_test")
        tid1 = client._next_trace_id()
        tid2 = client._next_trace_id()
        assert tid1 != tid2
        assert tid1.endswith("-000001")
        assert tid2.endswith("-000002")

    def test_trace_id_with_custom_session(self) -> None:
        trace = TraceConfig(session_id="mybot")
        client = BayseClient("pk_test", "sk_test", trace_config=trace)
        tid = client._next_trace_id()
        assert tid.startswith("mybot-")

    def test_use_outside_context_manager_raises(self) -> None:
        client = BayseClient("pk_test", "sk_test")
        with pytest.raises(RuntimeError, match="not open"):
            _ = client._client


class TestClientHeaders:
    """Tests for header building across auth levels."""

    def test_public_headers_no_auth(self) -> None:
        client = BayseClient("pk_test", "sk_test")
        headers = client._build_headers(method="GET", path="/health", body=None, trace_id=None, auth_level="public")
        assert "X-Public-Key" not in headers
        assert "X-Signature" not in headers
        assert "Content-Type" in headers

    def test_read_headers_include_public_key(self) -> None:
        client = BayseClient("pk_test_abc", "sk_test_xyz")
        headers = client._build_headers(method="GET", path="/v1/pm/events", body=None, trace_id=None, auth_level="read")
        assert headers["X-Public-Key"] == "pk_test_abc"
        assert "X-Signature" not in headers

    def test_write_headers_include_all(self) -> None:
        client = BayseClient("pk_test_abc", "sk_test_xyz")
        headers = client._build_headers(
            method="POST",
            path="/v1/pm/orders",
            body='{"side":"BUY"}',
            trace_id=None,
            auth_level="write",
        )
        assert headers["X-Public-Key"] == "pk_test_abc"
        assert "X-Timestamp" in headers
        assert "X-Signature" in headers

    def test_trace_id_override(self) -> None:
        client = BayseClient("pk_test", "sk_test")
        headers = client._build_headers(
            method="GET", path="/health", body=None, trace_id="custom-trace", auth_level="public"
        )
        assert headers["x-trace-id"] == "custom-trace"
