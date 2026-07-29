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
from bayse_markets._logging import get_logger
from bayse_markets._retry import RetryStrategy
from bayse_markets.exceptions import (
    NetworkError,
    classify_request_sent,
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
    PlaceOrderRequest,
    PlaceOrderResponse,
)
from bayse_markets.models.order_book import OrderBook
from bayse_markets.models.pnl import PnLResponse
from bayse_markets.models.portfolio import PortfolioResponse
from bayse_markets.models.price_history import PricePoint
from bayse_markets.models.quote import Quote, QuoteRequest
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

        if auth_level in ("read", "write") and self._public_key:
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
        idempotent: bool = False,
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
        replay_is_safe = self._retry.is_idempotent(method, idempotent=idempotent)

        attempt = 0
        while True:
            log.debug(
                "Request [%s %s] (attempt %d, trace=%s)",
                method,
                path,
                attempt + 1,
                headers.get("x-trace-id"),
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
                    message=f"Request timed out after {self._timeout}s ({type(exc).__name__})",
                    original_exception=exc,
                    request_sent=classify_request_sent(exc),
                )
            except httpx.HTTPError as exc:
                raise NetworkError(
                    message=f"HTTP transport error ({type(exc).__name__}): {exc}",
                    original_exception=exc,
                    request_sent=classify_request_sent(exc),
                )

            log.debug(
                "Response [%d] (trace=%s)",
                resp.status_code,
                resp.headers.get("x-trace-id"),
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

            if (
                self._retry.should_retry(
                    attempt,
                    resp.status_code,
                    method=method,
                    idempotent=idempotent,
                )
                and attempt < max_retries
            ):
                delay = self._retry.delay(attempt)
                if replay_is_safe:
                    log.debug(
                        "Retrying %s %s after %d (attempt %d, delay=%.2fs, trace=%s)",
                        method,
                        path,
                        resp.status_code,
                        attempt + 1,
                        delay,
                        headers.get("x-trace-id"),
                    )
                else:
                    # A retry of a non-idempotent call is an operator-visible event:
                    # it is the only signal that a duplicate may exist upstream.
                    log.warning(
                        "Retrying NON-IDEMPOTENT %s %s after %d "
                        "(attempt %d, delay=%.2fs, trace=%s)",
                        method,
                        path,
                        resp.status_code,
                        attempt + 1,
                        delay,
                        headers.get("x-trace-id"),
                    )
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
        """Check if the API is running.

        Args:
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response indicating API health status.
        """
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
        """Get the current deployed API version.

        Args:
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing the deployed version string.
        """
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
        """Get a paginated list of prediction market events.

        Supports filtering by category, status, keyword, currency,
        trending, watchlist, series slug, and sport game slug.

        Args:
            page: Page number (default 1).
            size: Results per page (default 20).
            category: Filter by event category.
            subcategory: Filter by event subcategory.
            status: Filter by event status.
            keyword: Search keyword.
            currency: ``"USD"`` or ``"NGN"``.
            trending: Filter to trending events.
            watchlist: Filter to watchlist events.
            series_slug: Filter by event series slug.
            sport_game_slug: Filter by sport game slug.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing a paginated list of events.
        """
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
        """Get a single prediction market event by ID.

        Args:
            event_id: UUID of the event.
            currency: ``"USD"`` or ``"NGN"`` for price display.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing the event details.
        """
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
        """Get a single prediction market event by its slug.

        Args:
            slug: Event slug (URL-friendly identifier).
            currency: ``"USD"`` or ``"NGN"`` for price display.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing the event details.
        """
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
        """Get a paginated list of event series.

        Args:
            page: Page number (default 1).
            size: Results per page, max 100 (default 50).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing a paginated list of event series.
        """
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
        """Get a lightweight list of events belonging to a series.

        Args:
            series_slug: Slug of the event series.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing a list of lean event summaries.
        """
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
        side: str,
        outcome_id: str,
        amount: float,
        currency: str = "USD",
        trace_id: str | None = None,
    ) -> BayseResponse[Quote]:
        """Get a price quote before placing an order.

        Returns the expected cost, shares, fees, and price impact for a
        potential trade without committing to it.

        Args:
            event_id: UUID of the event.
            market_id: UUID of the market.
            side: ``"BUY"`` or ``"SELL"``.
            outcome_id: UUID of the outcome.
            amount: Amount to spend (buy) or receive (sell).
            currency: ``"USD"`` (default) or ``"NGN"``.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing the quote details.
        """
        body = QuoteRequest(
            side=side,
            outcome_id=outcome_id,
            amount=amount,
            currency=currency,
        ).model_dump(by_alias=True, mode="json")
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
        side: str,
        outcome_id: str,
        amount: float,
        order_type: str,
        currency: str = "USD",
        price: float | None = None,
        time_in_force: str | None = None,
        post_only: bool | None = None,
        stp_mode: str | None = None,
        max_slippage: float | None = None,
        expires_at: str | None = None,
        trace_id: str | None = None,
        max_retries: int | None = None,
    ) -> BayseResponse[PlaceOrderResponse]:
        """Place a buy or sell order on a prediction market.

        Args:
            event_id: UUID of the event.
            market_id: UUID of the market.
            side: ``"BUY"`` or ``"SELL"``.
            outcome_id: UUID of the outcome.
            amount: Amount to spend (buy) or receive (sell).
            order_type: ``"LIMIT"`` or ``"MARKET"``.
            currency: ``"USD"`` (default) or ``"NGN"``.
            price: Limit price (required for ``LIMIT`` orders).
            time_in_force: ``"GTC"``, ``"GTD"``, ``"FAK"``, or ``"FOK"``.
            post_only: Whether to reject instead of crossing the spread.
            stp_mode: Self-trade prevention mode for CLOB markets. One of
                ``"SKIP"`` (default), ``"CANCEL_OLDEST"``, ``"CANCEL_NEWEST"``, or
                ``"CANCEL_BOTH"``. Unrecognised values fall back to ``"SKIP"``
                server-side without raising, so a typo silently disables
                self-trade prevention.
            max_slippage: Max acceptable slippage for ``MARKET`` orders. Accepted
                range is **0 to 0.50** — the API rejects anything outside it with
                ``400 "max slippage must be between 0 and 0.50"``. (Note
                ``api-reference.md:1149`` documents the range as 0.00–1.00 and is
                wrong.) The value is validated on submission but is **not echoed
                back** in any response field, so there is no way to confirm from
                the order which value was applied. Ignored for ``LIMIT`` orders,
                where the limit price is the price protection.
            expires_at: ISO 8601 expiration (required for ``GTD``).
            trace_id: Optional trace ID for request correlation.
            max_retries: Maximum retry attempts. See ``RetryConfig`` for which
                statuses are retried; non-idempotent calls use a narrower set.

        Returns:
            Response containing the placed order details.
        """
        body = PlaceOrderRequest(
            side=side,
            outcome_id=outcome_id,
            amount=amount,
            order_type=order_type,
            currency=currency,
            price=price,
            time_in_force=time_in_force,
            post_only=post_only,
            stp_mode=stp_mode,
            max_slippage=max_slippage,
            expires_at=expires_at,
        ).model_dump(by_alias=True, mode="json", exclude_none=True)
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
        """Get a paginated list of your orders.

        Supports filtering by side, status, event, market, outcome,
        and currency.

        .. warning::
            **Omitting** ``currency`` does not mean "all currencies" — the API
            returns an empty page. An account holding 60 NGN orders returns
            ``totalCount=0`` for both a bare call and ``currency="USD"``, with a
            ``200`` and well-formed pagination, so the mistake is invisible.

            Always pass ``currency`` explicitly, and call once per currency you
            trade. Never treat a bare call's empty result as "this account has no
            orders". This method logs a warning if it looks like you have.

            Values are case-sensitive: use ``"NGN"``, not ``"ngn"``.

        Args:
            side: Filter by side (``"BUY"`` or ``"SELL"``).
            status: Filter by status (``"open"``, ``"filled"``, etc.).
            event_id: Filter by event UUID.
            market_id: Filter by market UUID.
            outcome_id: Filter by outcome UUID.
            currency: Filter by currency (``"USD"`` or ``"NGN"``). Should always
                be supplied — see the warning above.
            page: Page number (default 1).
            size: Results per page (default 20).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing a paginated list of orders.
        """
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
        if currency is None and not parsed.orders:
            # An empty page here is far more often a missing `currency` filter
            # than an empty account, and nothing in the response distinguishes
            # the two. Anything reconciling state off this call would otherwise
            # conclude there is nothing to reconcile.
            log.warning(
                "list_orders() returned no orders and no currency filter was set. "
                "The API does not treat a missing 'currency' as 'all currencies' — "
                "it returns an empty page. Pass currency='NGN'/'USD' explicitly, "
                "once per currency you trade, before concluding this account is "
                "flat. (trace=%s)",
                resp.trace_id,
            )
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
        """Get details of a specific order by ID.

        Args:
            order_id: UUID of the order.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing the order details.
        """
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
        """Cancel an open or partially filled order.

        .. warning::
            This is an authenticated write operation.

        Args:
            order_id: UUID of the order to cancel.
            trace_id: Optional trace ID for request correlation.
            max_retries: Maximum retry attempts. See ``RetryConfig`` for which
                statuses are retried; non-idempotent calls use a narrower set.

        Returns:
            Response confirming the cancellation.
        """
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
        """Place up to 20 CLOB orders across one or more markets.

        The ``body`` must contain an ``orders`` array. Each order spec
        uses API field names (``marketId``, ``side``, ``outcomeId``, etc.).

        .. warning::
            This is an authenticated write operation.

        Args:
            body: Batch order payload with ``orders`` array.
            idempotency_key: Optional key for idempotent retries.
            trace_id: Optional trace ID for request correlation.
            max_retries: Maximum retry attempts. See ``RetryConfig`` for which
                statuses are retried; non-idempotent calls use a narrower set.

        Returns:
            Response containing batch placement results.
        """
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
            idempotent=idempotency_key is not None,
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
        """Modify the price or size of up to 20 open CLOB orders.

        The ``body`` must contain an ``orders`` array with order IDs
        and updated fields.

        .. warning::
            This is an authenticated write operation.

        Args:
            body: Batch amend payload with ``orders`` array.
            idempotency_key: Optional key for idempotent retries.
            trace_id: Optional trace ID for request correlation.
            max_retries: Maximum retry attempts. See ``RetryConfig`` for which
                statuses are retried; non-idempotent calls use a narrower set.

        Returns:
            Response containing batch amend results.
        """
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
            idempotent=idempotency_key is not None,
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
        """Cancel up to 100 CLOB orders across one or more markets.

        The ``body`` must contain an ``orderIds`` array.

        .. warning::
            This is an authenticated write operation.

        Args:
            body: Batch cancel payload with ``orderIds`` array.
            idempotency_key: Optional key for idempotent retries.
            trace_id: Optional trace ID for request correlation.
            max_retries: Maximum retry attempts. See ``RetryConfig`` for which
                statuses are retried; non-idempotent calls use a narrower set.

        Returns:
            Response containing batch cancellation results.
        """
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
        """Get your current positions across all markets.

        Returns outcome balances, market details, and total portfolio
        value for the authenticated user.

        Args:
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing portfolio positions.
        """
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
        """Get your realized profit and loss over a time period.

        Supports rolling windows (``"1M"``, ``"24H"``, etc.),
        calendar windows (``"THIS_WEEK"``), or custom date ranges.

        Args:
            time_period: Rolling (``"1M"``) or calendar window.
            start: Custom start time (ISO 8601). Paired with ``end``.
            end: Custom end time (ISO 8601). Paired with ``start``.
            currency: ``"USD"`` (default) or ``"NGN"``.
            breakdown: Include per-event breakdown (default ``False``).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing realized PnL data.
        """
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
        """Get wallet assets and balances for the authenticated user.

        Returns all currency assets including available and pending
        balances, deposit/withdrawal addresses, and per-asset network info.

        Args:
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing wallet assets with balances.
        """
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
        """Get historical price data for a prediction market event.

        Returns a map of market IDs to arrays of price points. No
        authentication required.

        Args:
            event_id: UUID of the event.
            time_period: Time window (``"24H"`` default, ``"1W"``, ``"1M"``, etc.).
            market_ids: Filter to specific market UUIDs.
            outcome: Filter to a specific outcome (``"YES"`` or ``"NO"``).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response mapping market IDs to lists of historical price points.
        """
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
        parsed: dict[str, list[PricePoint]] = {}
        for m in (resp.data.get("markets") or []):
            market_id = m["marketId"]
            outcome = m.get("title", "")
            pts = []
            for entry in (m.get("priceHistory") or []):
                pts.append(PricePoint(
                    outcome=outcome,
                    price=entry["p"],
                    timestamp=datetime.fromtimestamp(entry["e"] / 1000, tz=UTC),
                ))
            if pts:
                parsed[market_id] = pts
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
        """Get the live order book for one or more outcomes (CLOB only).

        Returns bids, asks, last traded price, and side for each
        requested outcome. No authentication required.

        Args:
            outcome_ids: One or more outcome UUIDs.
            depth: Number of price levels on each side (default 10).
            currency: Price display currency (default ``"USD"``).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing order books for the requested outcomes.
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
        """Get real-time price and volume statistics for a market outcome.

        Requires either ``outcome`` or ``outcome_id``.

        Args:
            market_id: UUID of the market.
            outcome: Outcome label (``"YES"`` or ``"NO"``). Required if ``outcome_id`` not provided.
            outcome_id: UUID of the outcome. Required if ``outcome`` not provided.
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing ticker data for the requested outcome.
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
        """Get recent executed trades (CLOB markets only).

        Use query params to filter by market, outcome, or time range.

        Args:
            params: Query parameters as a dict (``marketId``, ``outcomeId``, etc.).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing a list of executed trades.
        """
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
        """Get your trading activity history.

        Supports filtering by activity category.

        Args:
            type: Filter by activity category (``"buys"``, ``"sells"``, ``"limits"``, ``"payout"``).
            page: Page number (default 1).
            size: Items per page (default 20).
            trace_id: Optional trace ID for request correlation.

        Returns:
            Response containing a paginated list of activities.
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
