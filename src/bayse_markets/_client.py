from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import httpx

from bayse_markets._auth import SignerProtocol, sign_request
from bayse_markets._base import BayseResponse
from bayse_markets._config import (
    Env,
    RetryConfig,
    TraceConfig,
    base_url_for,
)
from bayse_markets._logging import get_logger, redact_headers
from bayse_markets._retry import RetryStrategy
from bayse_markets.exceptions import (
    NetworkError,
    error_from_response,
)

log = get_logger()


class BayseClient:
    """Async HTTP client for the Bayse Markets API.

    Use as an async context manager::

        async with BayseClient(public_key="pk_...", secret_key="sk_...") as client:
            events = await client.list_events()
    """

    def __init__(
        self,
        public_key: str,
        secret_key: str,
        *,
        env: str | Env = Env.PRODUCTION,
        trace_config: TraceConfig | None = None,
        retry_strategy: RetryStrategy | None = None,
        signer: SignerProtocol | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._public_key = public_key
        self._secret_key = secret_key

        if isinstance(env, str):
            env = Env(env)
        self._env = env
        self._base_url = base_url_for(env)

        self._trace = trace_config or TraceConfig()
        self._retry = retry_strategy or RetryStrategy(RetryConfig())
        self._signer = signer or sign_request
        self._timeout = timeout

        self._http: httpx.AsyncClient | None = None
        self._seq = self._trace.start_sequence
        self._session_id = self._trace.session_id

    def _next_trace_id(self) -> str:
        tid = f"{self._session_id}-{self._seq:06d}"
        self._seq += 1
        return tid

    async def __aenter__(self) -> BayseClient:
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            raise RuntimeError("BayseClient is not open. Use 'async with BayseClient(...) as client:'")
        return self._http

    def _build_headers(
        self,
        *,
        method: str,
        path: str,
        body: str | None,
        trace_id: str | None,
        auth_level: str,
    ) -> dict[str, str]:
        tid = trace_id or self._next_trace_id()
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "x-trace-id": tid,
        }

        if auth_level in ("read", "write"):
            headers["X-Public-Key"] = self._public_key

        if auth_level == "write":
            timestamp = int(datetime.now(UTC).timestamp())
            signature = self._signer(
                self._secret_key,
                timestamp=timestamp,
                method=method,
                path=path,
                body=body,
            )
            headers["X-Timestamp"] = str(timestamp)
            headers["X-Signature"] = signature

        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        auth_level: str = "public",
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[Any]:
        body_str = None
        if body is not None:
            body_str = __import__("json").dumps(body)

        headers = self._build_headers(
            method=method,
            path=path,
            body=body_str,
            trace_id=trace_id,
            auth_level=auth_level,
        )

        max_retries = max_retries if max_retries is not None else self._retry.config.max_retries

        attempt = 0
        while True:
            log.debug(
                "Request",
                extra={
                    "method": method,
                    "path": path,
                    "headers": redact_headers(headers),
                    "trace_id": headers.get("x-trace-id"),
                    "attempt": attempt + 1,
                },
            )

            try:
                resp = await self._client.request(
                    method,
                    path,
                    headers=headers,
                    content=body_str,
                    params=params,
                )
            except httpx.TimeoutException as exc:
                raise NetworkError(
                    message=f"Request timed out after {self._timeout}s",
                    original_exception=exc,
                )
            except httpx.HTTPError as exc:
                raise NetworkError(
                    message=f"HTTP transport error: {exc}",
                    original_exception=exc,
                )

            log.debug(
                "Response",
                extra={
                    "status": resp.status_code,
                    "trace_id": resp.headers.get("x-trace-id"),
                },
            )

            if resp.status_code < 400:
                data = resp.json()
                response_trace = resp.headers.get("x-trace-id")
                return BayseResponse(
                    status_code=resp.status_code,
                    data=data,
                    timestamp=datetime.now(UTC),
                    headers=dict(resp.headers),
                    trace_id=response_trace,
                )

            if self._retry.should_retry(attempt, resp.status_code) and attempt < max_retries:
                delay = self._retry.delay(attempt)
                log.debug("Retrying", extra={"attempt": attempt + 1, "delay": delay})
                await asyncio.sleep(delay)
                attempt += 1
                continue

            error_data = resp.json()
            error_code = error_data.get("error", "unknown_error")
            error_message = error_data.get("message", "Unknown error")
            raise error_from_response(
                error_code=error_code,
                message=error_message,
                status_code=resp.status_code,
                response_headers=dict(resp.headers),
                timestamp=datetime.now(UTC),
            )

    # ── System ──────────────────────────────────────────────────────────

    async def health(self, *, trace_id: str | None = None) -> BayseResponse[Any]:
        """GET /health — check API health."""
        return await self._request("GET", "/health", auth_level="public", trace_id=trace_id)

    async def version(self, *, trace_id: str | None = None) -> BayseResponse[Any]:
        """GET /version — get API version."""
        return await self._request("GET", "/version", auth_level="public", trace_id=trace_id)

    # ── Events ──────────────────────────────────────────────────────────

    async def list_events(
        self,
        *,
        page: int = 1,
        size: int = 20,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/events — list prediction market events."""
        return await self._request(
            "GET",
            "/v1/pm/events",
            params={"page": page, "size": size},
            auth_level="read",
            trace_id=trace_id,
        )

    async def get_event(
        self,
        event_id: str,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/events/{eventId} — get a single event."""
        return await self._request(
            "GET",
            f"/v1/pm/events/{event_id}",
            auth_level="read",
            trace_id=trace_id,
        )

    # ── Quoting ─────────────────────────────────────────────────────────

    async def get_quote(
        self,
        event_id: str,
        market_id: str,
        *,
        body: dict[str, Any],
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """POST /v1/pm/events/{eventId}/markets/{marketId}/quote — get a quote."""
        return await self._request(
            "POST",
            f"/v1/pm/events/{event_id}/markets/{market_id}/quote",
            body=body,
            auth_level="public",
            trace_id=trace_id,
        )

    # ── Orders ──────────────────────────────────────────────────────────

    async def place_order(
        self,
        event_id: str,
        market_id: str,
        *,
        body: dict[str, Any],
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[Any]:
        """POST /v1/pm/events/{eventId}/markets/{marketId}/orders — place an order."""
        return await self._request(
            "POST",
            f"/v1/pm/events/{event_id}/markets/{market_id}/orders",
            body=body,
            auth_level="write",
            trace_id=trace_id,
            max_retries=max_retries,
        )

    async def list_orders(
        self,
        *,
        page: int = 1,
        size: int = 20,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/orders — list orders."""
        return await self._request(
            "GET",
            "/v1/pm/orders",
            params={"page": page, "size": size},
            auth_level="read",
            trace_id=trace_id,
        )

    async def get_order(
        self,
        order_id: str,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/orders/{orderId} — get a single order."""
        return await self._request(
            "GET",
            f"/v1/pm/orders/{order_id}",
            auth_level="read",
            trace_id=trace_id,
        )

    async def cancel_order(
        self,
        order_id: str,
        *,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[Any]:
        """DELETE /v1/pm/orders/{orderId} — cancel an order."""
        return await self._request(
            "DELETE",
            f"/v1/pm/orders/{order_id}",
            auth_level="write",
            trace_id=trace_id,
            max_retries=max_retries,
        )

    # ── Portfolio ───────────────────────────────────────────────────────

    async def get_portfolio(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/portfolio — get portfolio."""
        return await self._request(
            "GET",
            "/v1/pm/portfolio",
            auth_level="read",
            trace_id=trace_id,
        )

    # ── Wallet ──────────────────────────────────────────────────────────

    async def get_assets(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/wallet/assets — get wallet assets."""
        return await self._request(
            "GET",
            "/v1/wallet/assets",
            auth_level="read",
            trace_id=trace_id,
        )

    # ── Market Data ─────────────────────────────────────────────────────

    async def get_price_history(
        self,
        event_id: str,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/events/{eventId}/price-history — get price history."""
        return await self._request(
            "GET",
            f"/v1/pm/events/{event_id}/price-history",
            auth_level="read",
            trace_id=trace_id,
        )

    async def get_order_books(
        self,
        *,
        params: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/books — get order books."""
        return await self._request(
            "GET",
            "/v1/pm/books",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )

    async def get_ticker(
        self,
        market_id: str,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/markets/{marketId}/ticker — get ticker."""
        return await self._request(
            "GET",
            f"/v1/pm/markets/{market_id}/ticker",
            auth_level="read",
            trace_id=trace_id,
        )

    async def get_trades(
        self,
        *,
        params: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/trades — get trades."""
        return await self._request(
            "GET",
            "/v1/pm/trades",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )

    # ── Activities ──────────────────────────────────────────────────────

    async def get_activities(
        self,
        *,
        params: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[Any]:
        """GET /v1/pm/activities — get account activities."""
        return await self._request(
            "GET",
            "/v1/pm/activities",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
