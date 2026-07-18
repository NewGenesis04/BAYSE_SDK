from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from bayse_markets._base import BayseResponse
from bayse_markets.models.event import Event, EventMarket
from bayse_markets.models.order_book import OrderBook
from bayse_markets.models.portfolio import PortfolioResponse
from bayse_markets.models.wallet import ListAssetsResponse
from bayse_markets.utils import (
    MarketSummary,
    OutcomeComparison,
    PortfolioBreakdown,
    SectorOverview,
    SpreadInfo,
    calculate_spread,
    compare_outcomes,
    get_closing_soon,
    get_high_volume_markets,
    get_market_summary,
    get_portfolio_breakdown,
    get_sector_overview,
)

_now = datetime.now(UTC)


def _e(id: str, **kw) -> Event:
    """Build Event using alias names."""
    d = dict(id=id, title=f"E{id[:8]}", status="open", closingDate=_now.isoformat(), markets=[])
    d.update(kw)
    return Event.model_validate(d)


def _book(market_id: str, outcome_id: str, bid: float, ask: float,
          last_price: float | None = None, bid_size: int = 1, ask_size: int = 1) -> OrderBook:
    return OrderBook.model_validate({
        "marketId": market_id,
        "outcomeId": outcome_id,
        "timestamp": _now.isoformat(),
        "bids": [{"price": bid, "quantity": 100, "total": bid * 100}] * bid_size,
        "asks": [{"price": ask, "quantity": 100, "total": ask * 100}] * ask_size,
        "lastTradedPrice": last_price,
        "lastTradedSide": "BUY" if last_price else None,
    })


def _br(data, code=200):
    return BayseResponse(
        status_code=code, data=data,
        timestamp=_now, headers={"x-trace-id": "test"}, trace_id="test",
    )


# ── get_closing_soon ──────────────────────────────────────────────────

class TestGetClosingSoon:
    async def test_filters_events_within_window(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", closingDate=(_now + timedelta(hours=2)).isoformat()),
            _e("b", closingDate=(_now + timedelta(hours=12)).isoformat()),
            _e("c", closingDate=(_now + timedelta(hours=48)).isoformat()),
            _e("d", status="closed", closingDate=(_now - timedelta(hours=1)).isoformat()),
        ]})())

        resp = await get_closing_soon(client, hours=24)
        assert {e.id for e in resp.data} == {"a", "b"}

    async def test_empty_when_no_events_close_soon(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", closingDate=(_now + timedelta(hours=48)).isoformat()),
        ]})())

        resp = await get_closing_soon(client, hours=24)
        assert len(resp.data) == 0

    async def test_passes_args_through(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", closingDate=(_now + timedelta(hours=2)).isoformat()),
        ]})())

        await get_closing_soon(client, hours=6, category="crypto", currency="NGN", page=2, size=10)

        client.list_events.assert_called_once_with(
            page=2, size=10, category="crypto", currency="NGN", trace_id=None,
        )


# ── get_high_volume_markets ──────────────────────────────────────────

class TestGetHighVolumeMarkets:
    async def test_filters_by_min_volume(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", totalVolume=10_000),
            _e("b", totalVolume=100_000),
            _e("c", totalVolume=500),
        ]})())

        resp = await get_high_volume_markets(client, min_volume=50_000)
        assert [e.id for e in resp.data] == ["b"]

    async def test_all_below_threshold(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", totalVolume=100),
        ]})())
        resp = await get_high_volume_markets(client, min_volume=500)
        assert len(resp.data) == 0

    async def test_skips_none_volume(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a"),
        ]})())
        resp = await get_high_volume_markets(client, min_volume=0)
        assert len(resp.data) == 0


# ── get_market_summary ───────────────────────────────────────────────

class TestGetMarketSummary:
    async def test_combines_event_and_order_books(self):
        client = AsyncMock()
        ev = _e("evt_0001", markets=[EventMarket.model_validate({
            "id": "mkt_0001", "title": "Mkt", "outcome1Id": "out_0001",
        })])
        client.get_event.return_value = _br(ev)
        client.get_order_books.return_value = _br([_book("mkt_0001", "out_0001", 0.70, 0.72)])

        resp = await get_market_summary(client, "evt_0001")
        s = resp.data
        assert isinstance(s, MarketSummary)
        assert s.event.id == "evt_0001"
        assert len(s.order_books) == 1
        assert s.order_books[0].outcome_id == "out_0001"

    async def test_empty_books_when_no_markets(self):
        client = AsyncMock()
        client.get_event.return_value = _br(_e("evt_0002"))
        resp = await get_market_summary(client, "evt_0002")
        assert resp.data.order_books == []

    async def test_skips_order_books_for_amm_event(self):
        client = AsyncMock()
        ev = _e("evt_0003", engine="AMM", markets=[EventMarket.model_validate({
            "id": "mkt_0001", "title": "Mkt", "outcome1Id": "out_0001",
        })])
        client.get_event.return_value = _br(ev)
        resp = await get_market_summary(client, "evt_0003")
        assert resp.data.order_books == []
        client.get_order_books.assert_not_called()

    async def test_passes_args_through(self):
        client = AsyncMock()
        ev = _e("evt_0003", markets=[EventMarket.model_validate({
            "id": "mkt_0001", "title": "Mkt", "outcome1Id": "out_0001",
        })])
        client.get_event.return_value = _br(ev)
        client.get_order_books.return_value = _br([_book("mkt_0001", "out_0001", 0.70, 0.72)])
        await get_market_summary(client, "evt_0003", depth=5, currency="NGN")
        client.get_order_books.assert_called_once_with(
            ["out_0001"], depth=5, currency="NGN", trace_id=None,
        )


# ── get_portfolio_breakdown ──────────────────────────────────────────

class TestGetPortfolioBreakdown:
    async def test_combines_portfolio_and_wallet(self):
        client = AsyncMock()
        client.get_portfolio.return_value = _br(PortfolioResponse.model_validate({
            "outcomeBalances": [{
                "id": "bal_0001", "outcome": "YES", "outcomeId": "out_0001",
                "assetId": "ast_0001", "balance": 138.21, "availableBalance": 138.21,
                "averagePrice": 0.7235, "cost": 100.0, "currentValue": 107.60,
                "sellPrice": 0.7786, "payoutIfOutcomeWins": 138.21,
                "percentageChange": 7.60, "currency": "USD", "userId": "usr_0001",
                "market": {
                    "id": "mkt_0001", "title": "Sample Market",
                    "event": {"id": "evt_0001", "title": "Sample Event"},
                },
                "createdAt": _now.isoformat(), "updatedAt": _now.isoformat(),
            }],
            "portfolioCost": 100.0,
            "portfolioCurrentValue": 107.60,
            "portfolioPercentageChange": 7.60,
            "pagination": {"page": 1, "size": 20, "lastPage": 1, "totalCount": 1},
        }))
        client.get_assets.return_value = _br(ListAssetsResponse.model_validate({
            "assets": [{
                "id": "ast_0001", "symbol": "USD", "userId": "usr_0001",
                "network": "LIGHTNING", "availableBalance": 500.0, "pendingBalance": 0.0,
                "depositActivity": "inactive", "withdrawalActivity": "inactive",
                "wagerActivity": "active", "isDefault": True,
                "isLocalCurrencyAsset": False, "addresses": [],
                "createdAt": _now.isoformat(), "updatedAt": _now.isoformat(),
            }],
        }))

        resp = await get_portfolio_breakdown(client)
        bd = resp.data

        assert isinstance(bd, PortfolioBreakdown)
        assert bd.portfolio_cost == 100.0
        assert bd.portfolio_current_value == 107.60
        assert len(bd.positions) == 1
        assert len(bd.assets) == 1
        assert bd.assets[0].available_balance == 500.0


# ── compare_outcomes ─────────────────────────────────────────────────

class TestCompareOutcomes:
    async def test_multiple_outcomes(self):
        client = AsyncMock()
        client.get_order_books.return_value = _br([
            _book("mkt_0001", "out_0001", 0.70, 0.72, last_price=0.71),
            _book("mkt_0002", "out_0002", 0.40, 0.55, last_price=0.48),
        ])
        resp = await compare_outcomes(client, ["out_0001", "out_0002"])
        assert len(resp.data) == 2
        assert all(isinstance(c, OutcomeComparison) for c in resp.data)

    async def test_computes_spread_correctly(self):
        client = AsyncMock()
        client.get_order_books.return_value = _br([
            _book("mkt_0001", "out_0001", 0.70, 0.72),
        ])
        c = (await compare_outcomes(client, ["out_0001"])).data[0]
        assert c.best_bid == 0.70
        assert c.best_ask == 0.72
        assert c.spread == pytest.approx(0.02)
        assert c.last_traded_price is None  # no last_price passed

    async def test_empty_books(self):
        client = AsyncMock()
        client.get_order_books.return_value = _br([
            _book("mkt_0003", "out_0003", 0, 0, bid_size=0, ask_size=0),
        ])
        c = (await compare_outcomes(client, ["out_0003"])).data[0]
        assert c.best_bid is None
        assert c.best_ask is None
        assert c.spread is None


# ── calculate_spread ─────────────────────────────────────────────────

class TestCalculateSpread:
    async def test_returns_spread_info(self):
        client = AsyncMock()
        client.get_order_books.return_value = _br([
            _book("mkt_0001", "out_0001", 0.70, 0.72, last_price=0.71),
        ])
        info = (await calculate_spread(client, "out_0001")).data
        assert isinstance(info, SpreadInfo)
        assert info.outcome_id == "out_0001"
        assert info.best_bid == 0.70
        assert info.best_ask == 0.72
        assert info.spread == pytest.approx(0.02)
        assert info.bid_depth == 1
        assert info.ask_depth == 1

    async def test_empty_book(self):
        client = AsyncMock()
        client.get_order_books.return_value = _br([
            _book("mkt_0001", "out_0001", 0, 0, bid_size=0, ask_size=0),
        ])
        info = (await calculate_spread(client, "out_0001")).data
        assert info.best_bid is None
        assert info.best_ask is None
        assert info.spread is None
        assert info.bid_depth == 0

    async def test_empty_response_list(self):
        client = AsyncMock()
        client.get_order_books.return_value = _br([])
        info = (await calculate_spread(client, "out_0001")).data
        assert info.best_bid is None
        assert info.best_ask is None
        assert info.spread is None
        assert info.market_id == ""


# ── get_sector_overview ──────────────────────────────────────────────

class TestGetSectorOverview:
    async def test_aggregates_metrics(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", totalVolume=100_000, liquidity=20_000, category="crypto"),
            _e("b", totalVolume=50_000, liquidity=10_000, category="crypto"),
            _e("c", totalVolume=10_000, liquidity=5_000, category="crypto", status="resolved"),
        ]})())

        s = (await get_sector_overview(client, "crypto")).data
        assert isinstance(s, SectorOverview)
        assert s.category == "crypto"
        assert s.event_count == 3
        assert s.total_volume == 160_000
        assert s.total_liquidity == 35_000
        assert s.average_volume == pytest.approx(53_333.33, rel=0.01)
        assert s.status_breakdown == {"open": 2, "resolved": 1}

    async def test_single_event(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": [
            _e("a", totalVolume=42_000, liquidity=8_000, category="politics"),
        ]})())
        s = (await get_sector_overview(client, "politics")).data
        assert s.event_count == 1
        assert s.average_volume == 42_000

    async def test_empty_category(self):
        client = AsyncMock()
        client.list_events.return_value = _br(type("E", (), {"events": []})())
        s = (await get_sector_overview(client, "nonexistent")).data
        assert s.event_count == 0
        assert s.total_volume == 0
        assert s.average_volume is None
