from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient
from bayse_markets._logging import get_logger
from bayse_markets.models.event import Event
from bayse_markets.models.order_book import OrderBook
from bayse_markets.models.portfolio import OutcomeBalance
from bayse_markets.models.wallet import Asset

log = get_logger()


@dataclass
class MarketSummary:
    event: Event
    order_books: list[OrderBook]


@dataclass
class PortfolioBreakdown:
    portfolio_cost: float
    portfolio_current_value: float
    portfolio_percentage_change: float
    positions: list[OutcomeBalance]
    assets: list[Asset]


@dataclass
class OutcomeComparison:
    outcome_id: str
    market_id: str
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    last_traded_price: float | None
    bid_depth: int
    ask_depth: int


@dataclass
class SpreadInfo:
    outcome_id: str
    market_id: str
    best_bid: float | None
    best_ask: float | None
    spread: float | None
    bid_depth: int
    ask_depth: int


@dataclass
class SectorOverview:
    category: str
    event_count: int
    total_volume: float
    total_liquidity: float
    status_breakdown: dict[str, int]
    average_volume: float | None


def _collect_outcome_ids(event: Event) -> list[str]:
    ids: list[str] = []
    for market in event.markets:
        if market.outcome1_id:
            ids.append(market.outcome1_id)
        if market.outcome2_id:
            ids.append(market.outcome2_id)
    return ids


def _compute_order_book_stats(book: OrderBook) -> tuple[float | None, float | None, float | None]:
    best_bid = book.bids[0].price if book.bids else None
    best_ask = book.asks[0].price if book.asks else None
    spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None
    return best_bid, best_ask, spread


async def get_closing_soon(
    client: BayseClient,
    *,
    hours: int = 24,
    page: int = 1,
    size: int = 50,
    category: str | None = None,
    currency: str | None = None,
    trace_id: str | None = None,
) -> BayseResponse[list[Event]]:
    """Find events closing within the specified number of hours.

    Fetches events from the API and filters by ``closing_date`` client-side.
    Only returns events that close within the next ``hours`` and haven't
    closed yet.

    Args:
        client: An open ``BayseClient`` instance.
        hours: Max hours until closing (default 24).
        page: Page number (default 1).
        size: Results per page (default 50).
        category: Filter by event category.
        currency: Filter by currency (``"USD"`` or ``"NGN"``).
        trace_id: Optional trace ID for request correlation.

    Returns:
        Filtered list of events closing soon.
    """
    events = await client.list_events(
        page=page,
        size=size,
        category=category,
        currency=currency,
        trace_id=trace_id,
    )
    now = datetime.now(UTC)
    cutoff = now + timedelta(hours=hours)
    closing = [
        e
        for e in events.data.events
        if e.closing_date is not None and now < e.closing_date <= cutoff
    ]
    return BayseResponse(
        status_code=events.status_code,
        data=closing,
        timestamp=events.timestamp,
        headers=events.headers,
        trace_id=events.trace_id,
    )


async def get_high_volume_markets(
    client: BayseClient,
    min_volume: float,
    *,
    page: int = 1,
    size: int = 50,
    category: str | None = None,
    currency: str | None = None,
    trace_id: str | None = None,
) -> BayseResponse[list[Event]]:
    """Get events with trading volume above a minimum threshold.

    Filters ``list_events()`` results by ``total_volume`` client-side.
    Returns events whose ``total_volume`` is >= ``min_volume``.

    Args:
        client: An open ``BayseClient`` instance.
        min_volume: Minimum total volume threshold.
        page: Page number (default 1).
        size: Results per page (default 50).
        category: Filter by event category.
        currency: Filter by currency.
        trace_id: Optional trace ID for request correlation.

    Returns:
        Filtered list of high-volume events.
    """
    events = await client.list_events(
        page=page,
        size=size,
        category=category,
        currency=currency,
        trace_id=trace_id,
    )
    high = [
        e
        for e in events.data.events
        if e.total_volume is not None and e.total_volume >= min_volume
    ]
    return BayseResponse(
        status_code=events.status_code,
        data=high,
        timestamp=events.timestamp,
        headers=events.headers,
        trace_id=events.trace_id,
    )


async def get_market_summary(
    client: BayseClient,
    event_id: str,
    *,
    depth: int = 10,
    currency: str = "USD",
    trace_id: str | None = None,
) -> BayseResponse[MarketSummary]:
    """Get a consolidated view of an event with its order books.

    Fetches the event details and order books for all outcomes in one
    call. Saves a round-trip vs calling ``get_event()`` and
    ``get_order_books()`` separately.

    .. note::
        Order books only exist for CLOB markets. Events with engine
        ``"AMM"`` will return an empty ``order_books`` list.

    Args:
        client: An open ``BayseClient`` instance.
        event_id: UUID of the event.
        depth: Order book depth per outcome (default 10).
        currency: Currency for prices (default ``"USD"``).
        trace_id: Optional trace ID for request correlation.

    Returns:
        A ``MarketSummary`` with the event and its order books.
    """
    event_resp = await client.get_event(event_id, currency=currency, trace_id=trace_id)
    event = event_resp.data
    if event.engine and event.engine != "CLOB":
        log.warning(
            "Event %s has engine %r — order books only exist for CLOB markets. "
            "Returning empty order books.", event_id, event.engine,
        )
        return BayseResponse(
            status_code=event_resp.status_code,
            data=MarketSummary(event=event, order_books=[]),
            timestamp=event_resp.timestamp,
            headers=event_resp.headers,
            trace_id=event_resp.trace_id,
        )
    outcome_ids = _collect_outcome_ids(event)
    if outcome_ids:
        books_resp = await client.get_order_books(
            outcome_ids, depth=depth, currency=currency, trace_id=trace_id,
        )
        order_books = books_resp.data
    else:
        order_books = []

    return BayseResponse(
        status_code=event_resp.status_code,
        data=MarketSummary(event=event_resp.data, order_books=order_books),
        timestamp=event_resp.timestamp,
        headers=event_resp.headers,
        trace_id=event_resp.trace_id,
    )


async def get_portfolio_breakdown(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[PortfolioBreakdown]:
    """Get a combined view of your portfolio positions and wallet assets.

    Fetches portfolio and wallet data in parallel. Provides a single
    response with all positions and available balances.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID for request correlation.

    Returns:
        A ``PortfolioBreakdown`` with positions and wallet assets.
    """
    import asyncio

    portfolio_resp, wallet_resp = await asyncio.gather(
        client.get_portfolio(trace_id=trace_id),
        client.get_assets(trace_id=trace_id),
    )
    p = portfolio_resp.data
    w = wallet_resp.data

    return BayseResponse(
        status_code=portfolio_resp.status_code,
        data=PortfolioBreakdown(
            portfolio_cost=p.portfolio_cost,
            portfolio_current_value=p.portfolio_current_value,
            portfolio_percentage_change=p.portfolio_percentage_change,
            positions=p.outcome_balances,
            assets=w.assets,
        ),
        timestamp=portfolio_resp.timestamp,
        headers=portfolio_resp.headers,
        trace_id=portfolio_resp.trace_id,
    )


async def compare_outcomes(
    client: BayseClient,
    outcome_ids: list[str],
    *,
    depth: int = 10,
    currency: str = "USD",
    trace_id: str | None = None,
) -> BayseResponse[list[OutcomeComparison]]:
    """Compare order book statistics across multiple outcomes.

    Fetches order books for all specified outcomes and computes
    best bid, best ask, and spread for each. Useful for scanning
    liquidity across related markets.

    .. note::
        Order books only exist for CLOB outcomes. AMM outcomes will
        return ``None`` for bid, ask, and spread.

    Args:
        client: An open ``BayseClient`` instance.
        outcome_ids: Outcome UUIDs to compare.
        depth: Order book depth per outcome (default 10).
        currency: Currency for prices (default ``"USD"``).
        trace_id: Optional trace ID for request correlation.

    Returns:
        List of outcome comparisons with spread data.
    """
    resp = await client.get_order_books(
        outcome_ids, depth=depth, currency=currency, trace_id=trace_id,
    )
    if not resp.data:
        log.warning(
            "No order book data for outcomes %s — may include AMM outcomes. "
            "Order books only exist for CLOB markets.", outcome_ids,
        )
    comparisons: list[OutcomeComparison] = []
    for book in resp.data:
        best_bid, best_ask, spread = _compute_order_book_stats(book)
        comparisons.append(OutcomeComparison(
            outcome_id=book.outcome_id,
            market_id=book.market_id,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            last_traded_price=book.last_traded_price,
            bid_depth=len(book.bids),
            ask_depth=len(book.asks),
        ))
    return BayseResponse(
        status_code=resp.status_code,
        data=comparisons,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def calculate_spread(
    client: BayseClient,
    outcome_id: str,
    *,
    depth: int = 10,
    currency: str = "USD",
    trace_id: str | None = None,
) -> BayseResponse[SpreadInfo]:
    """Calculate the bid-ask spread for a single outcome.

    .. note::
        Order books only exist for CLOB outcomes. AMM outcomes will
        return ``None`` for bid, ask, and spread.

    Args:
        client: An open ``BayseClient`` instance.
        outcome_id: Outcome UUID.
        depth: Order book depth (default 10).
        currency: Currency for prices (default ``"USD"``).
        trace_id: Optional trace ID for request correlation.

    Returns:
        Spread information for the outcome.
    """
    resp = await client.get_order_books(
        [outcome_id], depth=depth, currency=currency, trace_id=trace_id,
    )
    if not resp.data:
        log.warning(
            "No order book data for outcome %s — may be an AMM outcome. "
            "Order books only exist for CLOB markets.", outcome_id,
        )
        info = SpreadInfo(
            outcome_id=outcome_id, market_id="",
            best_bid=None, best_ask=None, spread=None,
            bid_depth=0, ask_depth=0,
        )
    else:
        book = resp.data[0]
        best_bid, best_ask, spread = _compute_order_book_stats(book)
        info = SpreadInfo(
            outcome_id=book.outcome_id,
            market_id=book.market_id,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            bid_depth=len(book.bids),
            ask_depth=len(book.asks),
        )
    return BayseResponse(
        status_code=resp.status_code,
        data=info,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def get_sector_overview(
    client: BayseClient,
    category: str,
    *,
    page: int = 1,
    size: int = 50,
    currency: str | None = None,
    trace_id: str | None = None,
) -> BayseResponse[SectorOverview]:
    """Get an aggregate view of all events in a category.

    Fetches events filtered by ``category`` and computes aggregate
    metrics: total volume, total liquidity, event count, and status
    breakdown.

    Args:
        client: An open ``BayseClient`` instance.
        category: Event category (e.g. ``"sports"``, ``"crypto"``, ``"politics"``).
        page: Page number (default 1).
        size: Results per page (default 50).
        currency: Filter by currency.
        trace_id: Optional trace ID for request correlation.

    Returns:
        Aggregated sector overview for the category.
    """
    events = await client.list_events(
        page=page,
        size=size,
        category=category,
        currency=currency,
        trace_id=trace_id,
    )
    all_events = events.data.events
    total_volume = sum(e.total_volume or 0 for e in all_events)
    total_liquidity = sum(e.liquidity or 0 for e in all_events)
    status_breakdown: dict[str, int] = {}
    for e in all_events:
        status_breakdown[e.status] = status_breakdown.get(e.status, 0) + 1
    return BayseResponse(
        status_code=events.status_code,
        data=SectorOverview(
            category=category,
            event_count=len(all_events),
            total_volume=total_volume,
            total_liquidity=total_liquidity,
            status_breakdown=status_breakdown,
            average_volume=total_volume / len(all_events) if all_events else None,
        ),
        timestamp=events.timestamp,
        headers=events.headers,
        trace_id=events.trace_id,
    )
