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
from bayse_markets.models.activity import ListActivitiesResponse
from bayse_markets.models.event import Event, LeanEvent, ListEventSeriesResponse, ListEventsResponse
from bayse_markets.models.order import (
    BatchAmendResponse,
    BatchCancelResponse,
    BatchPlaceResponse,
    CancelOrderResponse,
    ListOrdersResponse,
    Order,
    PlaceOrderResponse,
)
from bayse_markets.models.order_book import OrderBook
from bayse_markets.models.pnl import PnLResponse
from bayse_markets.models.portfolio import PortfolioResponse
from bayse_markets.models.price_history import PricePoint
from bayse_markets.models.quote import Quote
from bayse_markets.models.system import HealthResponse, VersionResponse
from bayse_markets.models.ticker import Ticker
from bayse_markets.models.trade import ListTradesResponse
from bayse_markets.models.wallet import ListAssetsResponse

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
        headers: dict[str, str] | None = None,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[Any]:
        body_str = None
        if body is not None:
            body_str = __import__("json").dumps(body)

        base_headers = self._build_headers(
            method=method,
            path=path,
            body=body_str,
            trace_id=trace_id,
            auth_level=auth_level,
        )
        if headers:
            base_headers.update(headers)
        headers = base_headers

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

    async def health(self, *, trace_id: str | None = None) -> BayseResponse[HealthResponse]:
        """GET /health — check API health."""
        resp = await self._request("GET", "/health", auth_level="public", trace_id=trace_id)
        parsed = HealthResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def version(self, *, trace_id: str | None = None) -> BayseResponse[VersionResponse]:
        """GET /version — get API version."""
        resp = await self._request("GET", "/version", auth_level="public", trace_id=trace_id)
        parsed = VersionResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Events ──────────────────────────────────────────────────────────

    async def list_events(
        self,
        *,
        page: int = 1,
        size: int = 20,
        category: str | None = None,
        subcategory: str | None = None,
        status: str | None = None,
        keyword: str | None = None,
        currency: str | None = None,
        trending: bool | None = None,
        watchlist: bool | None = None,
        series_slug: str | None = None,
        sport_game_slug: str | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[ListEventsResponse]:
        """GET /v1/pm/events — list prediction market events."""
        params: dict[str, Any] = {"page": page, "size": size}
        if category is not None:
            params["category"] = category
        if subcategory is not None:
            params["subcategory"] = subcategory
        if status is not None:
            params["status"] = status
        if keyword is not None:
            params["keyword"] = keyword
        if currency is not None:
            params["currency"] = currency
        if trending is not None:
            params["trending"] = str(trending).lower()
        if watchlist is not None:
            params["watchlist"] = str(watchlist).lower()
        if series_slug is not None:
            params["seriesSlug"] = series_slug
        if sport_game_slug is not None:
            params["sportGameSlug"] = sport_game_slug

        resp = await self._request(
            "GET",
            "/v1/pm/events",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = ListEventsResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_event(
        self,
        event_id: str,
        *,
        currency: str | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[Event]:
        """GET /v1/pm/events/{eventId} — get a single event."""
        params: dict[str, Any] = {}
        if currency is not None:
            params["currency"] = currency

        resp = await self._request(
            "GET",
            f"/v1/pm/events/{event_id}",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = Event.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_event_by_slug(
        self,
        slug: str,
        *,
        currency: str | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[Event]:
        """GET /v1/pm/events/slug/{slug} — get a single event by slug."""
        params: dict[str, Any] = {}
        if currency is not None:
            params["currency"] = currency

        resp = await self._request(
            "GET",
            f"/v1/pm/events/slug/{slug}",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = Event.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def list_event_series(
        self,
        *,
        page: int = 1,
        size: int = 50,
        trace_id: str | None = None,
    ) -> BayseResponse[ListEventSeriesResponse]:
        """GET /v1/pm/events/series — list event series."""
        resp = await self._request(
            "GET",
            "/v1/pm/events/series",
            params={"page": page, "size": size},
            auth_level="public",
            trace_id=trace_id,
        )
        parsed = ListEventSeriesResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_lean_events(
        self,
        series_slug: str,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[list[LeanEvent]]:
        """GET /v1/pm/events/series/{seriesSlug}/lean-events — get lean events for a series."""
        resp = await self._request(
            "GET",
            f"/v1/pm/events/series/{series_slug}/lean-events",
            auth_level="public",
            trace_id=trace_id,
        )
        parsed = [LeanEvent.model_validate(item) for item in resp.data]
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Quoting ─────────────────────────────────────────────────────────

    async def get_quote(
        self,
        event_id: str,
        market_id: str,
        *,
        body: dict[str, Any],
        trace_id: str | None = None,
    ) -> BayseResponse[Quote]:
        """POST /v1/pm/events/{eventId}/markets/{marketId}/quote — get a quote."""
        resp = await self._request(
            "POST",
            f"/v1/pm/events/{event_id}/markets/{market_id}/quote",
            body=body,
            auth_level="public",
            trace_id=trace_id,
        )
        parsed = Quote.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
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
    ) -> BayseResponse[PlaceOrderResponse]:
        """POST /v1/pm/events/{eventId}/markets/{marketId}/orders — place an order."""
        resp = await self._request(
            "POST",
            f"/v1/pm/events/{event_id}/markets/{market_id}/orders",
            body=body,
            auth_level="write",
            trace_id=trace_id,
            max_retries=max_retries,
        )
        parsed = PlaceOrderResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def list_orders(
        self,
        *,
        side: str | None = None,
        status: str | None = None,
        event_id: str | None = None,
        market_id: str | None = None,
        outcome_id: str | None = None,
        currency: str | None = None,
        page: int = 1,
        size: int = 20,
        trace_id: str | None = None,
    ) -> BayseResponse[ListOrdersResponse]:
        """GET /v1/pm/orders — list orders."""
        params: dict[str, Any] = {"page": page, "size": size}
        if side is not None:
            params["side"] = side
        if status is not None:
            params["status"] = status
        if event_id is not None:
            params["eventId"] = event_id
        if market_id is not None:
            params["marketId"] = market_id
        if outcome_id is not None:
            params["outcomeId"] = outcome_id
        if currency is not None:
            params["currency"] = currency
        resp = await self._request(
            "GET",
            "/v1/pm/orders",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = ListOrdersResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_order(
        self,
        order_id: str,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[Order]:
        """GET /v1/pm/orders/{orderId} — get a single order."""
        resp = await self._request(
            "GET",
            f"/v1/pm/orders/{order_id}",
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = Order.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def cancel_order(
        self,
        order_id: str,
        *,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[CancelOrderResponse]:
        """DELETE /v1/pm/orders/{orderId} — cancel an order."""
        resp = await self._request(
            "DELETE",
            f"/v1/pm/orders/{order_id}",
            auth_level="write",
            trace_id=trace_id,
            max_retries=max_retries,
        )
        parsed = CancelOrderResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Batch Orders ────────────────────────────────────────────────────

    async def batch_place_orders(
        self,
        *,
        body: dict[str, Any],
        idempotency_key: str | None = None,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[BatchPlaceResponse]:
        """POST /v1/pm/orders/batch — place up to 20 orders in one round-trip."""
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        resp = await self._request(
            "POST",
            "/v1/pm/orders/batch",
            body=body,
            auth_level="write",
            headers=headers,
            trace_id=trace_id,
            max_retries=max_retries,
        )
        parsed = BatchPlaceResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def batch_amend_orders(
        self,
        *,
        body: dict[str, Any],
        idempotency_key: str | None = None,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[BatchAmendResponse]:
        """POST /v1/pm/orders/batch/amend — modify price/size of up to 20 orders."""
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        resp = await self._request(
            "POST",
            "/v1/pm/orders/batch/amend",
            body=body,
            auth_level="write",
            headers=headers,
            trace_id=trace_id,
            max_retries=max_retries,
        )
        parsed = BatchAmendResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def batch_cancel_orders(
        self,
        *,
        body: dict[str, Any],
        idempotency_key: str | None = None,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[BatchCancelResponse]:
        """DELETE /v1/pm/orders/batch — cancel up to 100 orders in one round-trip."""
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        resp = await self._request(
            "DELETE",
            "/v1/pm/orders/batch",
            body=body,
            auth_level="write",
            headers=headers,
            trace_id=trace_id,
            max_retries=max_retries,
        )
        parsed = BatchCancelResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Portfolio ───────────────────────────────────────────────────────

    async def get_portfolio(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[PortfolioResponse]:
        """GET /v1/pm/portfolio — get portfolio."""
        resp = await self._request(
            "GET",
            "/v1/pm/portfolio",
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = PortfolioResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── PnL ─────────────────────────────────────────────────────────────

    async def get_pnl(
        self,
        *,
        time_period: str | None = None,
        start: str | None = None,
        end: str | None = None,
        currency: str | None = None,
        breakdown: bool = False,
        trace_id: str | None = None,
    ) -> BayseResponse[PnLResponse]:
        """GET /v1/pm/pnl — get realized profit and loss."""
        params: dict[str, Any] = {}
        if time_period is not None:
            params["timePeriod"] = time_period
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        if currency is not None:
            params["currency"] = currency
        if breakdown:
            params["breakdown"] = "true"

        resp = await self._request(
            "GET",
            "/v1/pm/pnl",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = PnLResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Wallet ──────────────────────────────────────────────────────────

    async def get_assets(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[ListAssetsResponse]:
        """GET /v1/wallet/assets — get wallet assets."""
        resp = await self._request(
            "GET",
            "/v1/wallet/assets",
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = ListAssetsResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Market Data ─────────────────────────────────────────────────────

    async def get_price_history(
        self,
        event_id: str,
        *,
        time_period: str = "24H",
        market_ids: list[str] | None = None,
        outcome: str | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[dict[str, list[PricePoint]]]:
        """GET /v1/pm/events/{eventId}/price-history — get price history."""
        params: dict[str, Any] = {"timePeriod": time_period}
        if market_ids is not None:
            params["marketId[]"] = ",".join(market_ids)
        if outcome is not None:
            params["outcome"] = outcome

        resp = await self._request(
            "GET",
            f"/v1/pm/events/{event_id}/price-history",
            params=params,
            auth_level="public",
            trace_id=trace_id,
        )
        parsed: dict[str, list[PricePoint]] = {
            market_id: [PricePoint.model_validate(p) for p in points]
            for market_id, points in resp.data.items()
        }
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_order_books(
        self,
        outcome_ids: list[str],
        *,
        depth: int = 10,
        currency: str = "USD",
        trace_id: str | None = None,
    ) -> BayseResponse[list[OrderBook]]:
        """GET /v1/pm/books — get order books for one or more outcomes.

        Args:
            outcome_ids: One or more outcome UUIDs.
            depth: Number of price levels on each side (default 10).
            currency: Price display currency (default ``"USD"``).
            trace_id: Optional trace ID override.
        """
        params: dict[str, Any] = {"depth": depth, "currency": currency}
        params["outcomeId[]"] = outcome_ids

        resp = await self._request(
            "GET",
            "/v1/pm/books",
            params=params,
            auth_level="public",
            trace_id=trace_id,
        )
        parsed = [OrderBook.model_validate(item) for item in resp.data]
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_ticker(
        self,
        market_id: str,
        *,
        outcome: str | None = None,
        outcome_id: str | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[Ticker]:
        """GET /v1/pm/markets/{marketId}/ticker — get ticker.

        Args:
            market_id: UUID of the market.
            outcome: Outcome label (``"YES"`` or ``"NO"``). Required if ``outcome_id`` not provided.
            outcome_id: UUID of the outcome. Required if ``outcome`` not provided.
            trace_id: Optional trace ID override.
        """
        params: dict[str, Any] = {}
        if outcome is not None:
            params["outcome"] = outcome
        if outcome_id is not None:
            params["outcomeId"] = outcome_id

        resp = await self._request(
            "GET",
            f"/v1/pm/markets/{market_id}/ticker",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = Ticker.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    async def get_trades(
        self,
        *,
        params: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[ListTradesResponse]:
        """GET /v1/pm/trades — get trades."""
        resp = await self._request(
            "GET",
            "/v1/pm/trades",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = ListTradesResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )

    # ── Activities ──────────────────────────────────────────────────────

    async def get_activities(
        self,
        *,
        type: str | None = None,
        page: int = 1,
        size: int = 20,
        trace_id: str | None = None,
    ) -> BayseResponse[ListActivitiesResponse]:
        """GET /v1/pm/activities — get account activities.

        Args:
            type: Filter by activity category (``"buys"``, ``"sells"``, ``"limits"``, ``"payout"``).
            page: Page number (default 1).
            size: Items per page (default 20).
            trace_id: Optional trace ID override.
        """
        params: dict[str, Any] = {"page": page, "size": size}
        if type is not None:
            params["type"] = type

        resp = await self._request(
            "GET",
            "/v1/pm/activities",
            params=params,
            auth_level="read",
            trace_id=trace_id,
        )
        parsed = ListActivitiesResponse.model_validate(resp.data)
        return BayseResponse(
            status_code=resp.status_code,
            data=parsed,
            timestamp=resp.timestamp,
            headers=resp.headers,
            trace_id=resp.trace_id,
        )
