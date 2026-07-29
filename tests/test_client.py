from __future__ import annotations

import logging
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from bayse_markets._client import BayseClient
from bayse_markets._config import Env, RetryConfig, TraceConfig
from bayse_markets._retry import RetryStrategy
from bayse_markets.exceptions import BayseError, NetworkError


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


class TestMethodAwareRetryAtCallSite:
    """The retry decision must reach the transport, not just the strategy."""

    @staticmethod
    def _client_returning(
        status: int,
        *,
        calls: list[str],
        retry_unsafe_on_statuses: tuple[int, ...] = (),
    ) -> BayseClient:
        client = BayseClient("pk_test", "sk_test")

        async def _request(method: str, path: str, **kwargs: object) -> httpx.Response:
            calls.append(method)
            return httpx.Response(
                status_code=status,
                json={"error": "internal_server_error", "message": "boom"},
                headers={"x-trace-id": "test-000001"},
            )

        transport = Mock(spec=httpx.AsyncClient)
        transport.request = _request
        client._http = transport
        client._retry = RetryStrategy(
            RetryConfig(
                max_retries=2,
                base_delay=0.0,
                jitter=0.0,
                retry_unsafe_on_statuses=retry_unsafe_on_statuses,
            )
        )
        return client

    @pytest.mark.asyncio
    async def test_post_is_not_retried_on_502(self) -> None:
        calls: list[str] = []
        client = self._client_returning(502, calls=calls)

        with pytest.raises(BayseError):
            await client._request("POST", "/v1/pm/orders", body={"a": 1}, auth_level="write")

        assert calls == ["POST"], "a POST that may have been processed was replayed"

    @pytest.mark.asyncio
    async def test_get_is_retried_on_502(self) -> None:
        calls: list[str] = []
        client = self._client_returning(502, calls=calls)

        with pytest.raises(BayseError):
            await client._request("GET", "/v1/pm/events")

        assert len(calls) == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_delete_is_retried_on_502(self) -> None:
        calls: list[str] = []
        client = self._client_returning(502, calls=calls)

        with pytest.raises(BayseError):
            await client._request("DELETE", "/v1/pm/orders/abc", auth_level="write")

        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_post_is_not_retried_on_429_by_default(self) -> None:
        calls: list[str] = []
        client = self._client_returning(429, calls=calls)

        with pytest.raises(BayseError):
            await client._request("POST", "/v1/pm/orders", body={"a": 1}, auth_level="write")

        assert calls == ["POST"], "a rate-limited write was replayed without opt-in"

    @pytest.mark.asyncio
    async def test_post_retries_on_429_when_the_caller_opts_in(self) -> None:
        calls: list[str] = []
        client = self._client_returning(429, calls=calls, retry_unsafe_on_statuses=(429,))

        with pytest.raises(BayseError):
            await client._request("POST", "/v1/pm/orders", body={"a": 1}, auth_level="write")

        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_idempotent_flag_reenables_502_retry_on_post(self) -> None:
        calls: list[str] = []
        client = self._client_returning(502, calls=calls)

        with pytest.raises(BayseError):
            await client._request(
                "POST", "/v1/pm/orders/batch", body={"a": 1}, auth_level="write", idempotent=True
            )

        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_unsafe_retry_logs_at_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        calls: list[str] = []
        client = self._client_returning(429, calls=calls, retry_unsafe_on_statuses=(429,))

        with caplog.at_level(logging.WARNING, logger="bayse_markets"), pytest.raises(BayseError):
            await client._request(
                "POST",
                "/v1/pm/orders",
                body={"a": 1},
                auth_level="write",
                trace_id="mybot-000042",
            )

        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "a replayed write left no trace in the operator's scrollback"
        assert "NON-IDEMPOTENT" in warnings[0].getMessage()
        assert "mybot-000042" in warnings[0].getMessage()
        assert "attempt 1" in warnings[0].getMessage()

    @pytest.mark.asyncio
    async def test_safe_retry_does_not_log_at_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        calls: list[str] = []
        client = self._client_returning(502, calls=calls)

        with caplog.at_level(logging.DEBUG, logger="bayse_markets"), pytest.raises(BayseError):
            await client._request("GET", "/v1/pm/events")

        assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


class TestNetworkErrorClassification:
    """Whether the request left the machine decides REJECTED vs UNKNOWN."""

    @staticmethod
    def _client_raising(exc: Exception) -> BayseClient:
        client = BayseClient("pk_test", "sk_test")
        transport = Mock(spec=httpx.AsyncClient)
        transport.request = AsyncMock(side_effect=exc)
        client._http = transport
        return client

    @pytest.mark.asyncio
    async def test_connect_error_is_definitively_not_sent(self) -> None:
        client = self._client_raising(httpx.ConnectError("refused"))

        with pytest.raises(NetworkError) as exc_info:
            await client._request("POST", "/v1/pm/orders", body={"a": 1}, auth_level="write")

        assert exc_info.value.request_sent is False

    @pytest.mark.asyncio
    async def test_connect_timeout_is_definitively_not_sent(self) -> None:
        client = self._client_raising(httpx.ConnectTimeout("timed out connecting"))

        with pytest.raises(NetworkError) as exc_info:
            await client._request("POST", "/v1/pm/orders", body={"a": 1}, auth_level="write")

        assert exc_info.value.request_sent is False

    @pytest.mark.asyncio
    async def test_read_timeout_is_ambiguous(self) -> None:
        client = self._client_raising(httpx.ReadTimeout("timed out reading"))

        with pytest.raises(NetworkError) as exc_info:
            await client._request("POST", "/v1/pm/orders", body={"a": 1}, auth_level="write")

        assert exc_info.value.request_sent is None

    @pytest.mark.asyncio
    async def test_original_exception_class_is_preserved(self) -> None:
        original = httpx.ReadTimeout("timed out reading")
        client = self._client_raising(original)

        with pytest.raises(NetworkError) as exc_info:
            await client._request("GET", "/v1/pm/events")

        assert exc_info.value.original_exception is original
        assert "ReadTimeout" in str(exc_info.value)


class TestListOrdersCurrencyGuard:
    """An empty page from a bare list_orders() is a trap, not a fact."""

    @staticmethod
    def _client_returning(orders: list[dict]) -> BayseClient:
        client = BayseClient("pk_test", "sk_test")
        payload = {
            "orders": orders,
            "pagination": {
                "page": 1,
                "size": 20,
                "lastPage": 1,
                "totalCount": len(orders),
            },
        }
        transport = Mock(spec=httpx.AsyncClient)
        transport.request = AsyncMock(
            return_value=httpx.Response(
                status_code=200, json=payload, headers={"x-trace-id": "test-000001"}
            )
        )
        client._http = transport
        return client

    ORDER = {
        "id": "d5cfd1b2-e445-4fa1-b949-06baf62bb21f",
        "marketId": "a0922e06-a65a-46cb-95dc-96f3270a7bad",
        "outcomeId": "25d84c55-f0fa-4b5d-a928-5ee67557d1a8",
        "side": "BUY",
        "type": "LIMIT",
        "stpMode": "SKIP",
        "status": "open",
        "amount": 100,
        "price": 0.01,
        "size": 99.99,
        "filledSize": 0,
        "remainingSize": 99.99,
        "currency": "NGN",
        "createdAt": "2026-07-28T23:42:38Z",
        "updatedAt": "2026-07-28T23:42:38Z",
    }

    @pytest.mark.asyncio
    async def test_warns_on_empty_result_without_currency(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        client = self._client_returning([])

        with caplog.at_level(logging.WARNING, logger="bayse_markets"):
            resp = await client.list_orders()

        assert resp.data.orders == []
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings, "an empty page with no currency filter passed silently"
        assert "currency" in warnings[0].getMessage()

    @pytest.mark.asyncio
    async def test_no_warning_when_currency_was_supplied(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An empty result IS meaningful once the caller has scoped the query."""
        client = self._client_returning([])

        with caplog.at_level(logging.WARNING, logger="bayse_markets"):
            await client.list_orders(currency="NGN")

        assert not [r for r in caplog.records if r.levelno == logging.WARNING]

    @pytest.mark.asyncio
    async def test_no_warning_when_orders_were_returned(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        client = self._client_returning([self.ORDER])

        with caplog.at_level(logging.WARNING, logger="bayse_markets"):
            resp = await client.list_orders()

        assert len(resp.data.orders) == 1
        assert not [r for r in caplog.records if r.levelno == logging.WARNING]

    @pytest.mark.asyncio
    async def test_currency_is_forwarded_as_a_query_param(self) -> None:
        client = self._client_returning([self.ORDER])

        await client.list_orders(currency="NGN")

        assert client._http.request.await_args.kwargs["params"]["currency"] == "NGN"

    @pytest.mark.asyncio
    async def test_live_shaped_order_parses_with_outcome_id(self) -> None:
        """Guards the §9 finding: the list route sends outcomeId, not outcome."""
        client = self._client_returning([self.ORDER])

        resp = await client.list_orders(currency="NGN")

        assert resp.data.orders[0].outcome_id == "25d84c55-f0fa-4b5d-a928-5ee67557d1a8"
