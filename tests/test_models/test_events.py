from __future__ import annotations

import pytest

from bayse_markets.models.event import (
    Event,
    EventMarket,
    EventSeries,
    LeanEvent,
    ListEventSeriesResponse,
    ListEventsResponse,
)


class TestEventMarketModel:
    """Tests for the EventMarket model."""

    def test_parse_full_market(self, sample_market: dict) -> None:
        market = EventMarket.model_validate(sample_market)
        assert market.id == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        assert market.title == "Will Super Eagles qualify?"
        assert market.status == "open"
        assert market.outcome1_label == "YES"
        assert market.outcome1_price == 0.72
        assert market.minimum_order_amount == 1
        assert market.fee_percentage == 2.0
        assert market.rules is not None

    def test_parse_market_with_prop_team(self, sample_market_with_prop: dict) -> None:
        market = EventMarket.model_validate(sample_market_with_prop)
        assert market.prop_team is not None
        assert market.prop_team.name == "Manchester City FC"
        assert market.prop_line == 1.5

    def test_parse_market_with_liquidity_reward(self, sample_market_with_reward: dict) -> None:
        market = EventMarket.model_validate(sample_market_with_reward)
        assert market.liquidity_reward is not None
        assert market.liquidity_reward.reward_pool == 5000

    def test_round_trip(self, sample_market: dict) -> None:
        market = EventMarket.model_validate(sample_market)
        serialised = market.model_dump(mode="json", by_alias=True, exclude_none=True)
        EventMarket.model_validate(serialised)


class TestEventModel:
    """Tests for the Event model."""

    def test_parse_simple_event(self, sample_simple_event: dict) -> None:
        event = Event.model_validate(sample_simple_event)
        assert event.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert event.title == "Will Super Eagles qualify for AFCON 2026?"
        assert event.status == "open"
        assert event.category == "sports"
        assert event.engine == "AMM"
        assert len(event.markets) == 1

    def test_parse_crypto_event(self, sample_crypto_event: dict) -> None:
        event = Event.model_validate(sample_crypto_event)
        assert event.asset_symbol_pair == "BTCUSDT"
        assert event.event_threshold == 96250.50
        assert event.series_slug == "crypto-btc-1h"
        assert event.opening_date is not None

    def test_parse_combined_event(self, sample_combined_event: dict) -> None:
        event = Event.model_validate(sample_combined_event)
        assert event.type == "combined"
        assert event.engine == "CLOB"
        assert event.sport_market_type == "TEAM_H2H_3WAY"
        assert event.sport_game_slug == "bm-game-20260524-mci-avl"
        assert len(event.markets) == 3

    def test_user_watchlisted(self, sample_combined_event: dict) -> None:
        event = Event.model_validate(sample_combined_event)
        assert event.user_watchlisted is True

    def test_round_trip(self, sample_simple_event: dict) -> None:
        event = Event.model_validate(sample_simple_event)
        serialised = event.model_dump(mode="json", by_alias=True, exclude_none=True)
        Event.model_validate(serialised)


class TestListEventsResponse:
    """Tests for the ListEventsResponse model."""

    def test_parse(self, sample_list_response: dict) -> None:
        resp = ListEventsResponse.model_validate(sample_list_response)
        assert len(resp.events) == 2
        assert resp.pagination.page == 1
        assert resp.pagination.total_count == 28

    def test_round_trip(self, sample_list_response: dict) -> None:
        resp = ListEventsResponse.model_validate(sample_list_response)
        serialised = resp.model_dump(mode="json", by_alias=True, exclude_none=True)
        ListEventsResponse.model_validate(serialised)


class TestEventSeriesModel:
    """Tests for the EventSeries model."""

    def test_parse(self, sample_series: dict) -> None:
        series = EventSeries.model_validate(sample_series)
        assert series.id == "f1e2d3c4-b5a6-7890-abcd-ef1234567890"
        assert series.slug == "crypto-btc-1h"
        assert series.display_name == "Bitcoin Hourly Markets"
        assert series.interval_type == "HOURLY"
        assert series.asset_symbol == "BTC"

    def test_round_trip(self, sample_series: dict) -> None:
        series = EventSeries.model_validate(sample_series)
        serialised = series.model_dump(mode="json", by_alias=True, exclude_none=True)
        EventSeries.model_validate(serialised)


class TestListEventSeriesResponse:
    """Tests for the ListEventSeriesResponse model."""

    def test_parse(self, sample_series_list_response: dict) -> None:
        resp = ListEventSeriesResponse.model_validate(sample_series_list_response)
        assert len(resp.series) == 2
        assert resp.pagination.total_count == 12
        assert resp.series[1].asset_symbol == "ETH"

    def test_round_trip(self, sample_series_list_response: dict) -> None:
        resp = ListEventSeriesResponse.model_validate(sample_series_list_response)
        serialised = resp.model_dump(mode="json", by_alias=True, exclude_none=True)
        ListEventSeriesResponse.model_validate(serialised)


class TestLeanEventModel:
    """Tests for the LeanEvent model."""

    def test_parse(self) -> None:
        data = {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "title": "Bitcoin Hourly — Feb 24 11am GMT",
            "openingDate": "2025-02-24T11:00:00Z",
            "closingDate": "2025-02-24T12:00:00Z",
            "resolutionDate": "2025-02-24T12:01:00Z",
        }
        lean = LeanEvent.model_validate(data)
        assert lean.title == "Bitcoin Hourly — Feb 24 11am GMT"
        assert lean.opening_date is not None
        assert lean.resolution_date is not None

    def test_minimal_fields(self) -> None:
        data = {"id": "abc", "title": "Test"}
        lean = LeanEvent.model_validate(data)
        assert lean.id == "abc"
        assert lean.opening_date is None

    def test_round_trip(self) -> None:
        data = {
            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "title": "Bitcoin Hourly — Feb 24 11am GMT",
            "openingDate": "2025-02-24T11:00:00Z",
            "closingDate": "2025-02-24T12:00:00Z",
            "resolutionDate": "2025-02-24T12:01:00Z",
        }
        lean = LeanEvent.model_validate(data)
        serialised = lean.model_dump(mode="json", by_alias=True, exclude_none=True)
        LeanEvent.model_validate(serialised)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_market() -> dict:
    return {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "title": "Will Super Eagles qualify?",
        "status": "open",
        "outcome1Id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "outcome1Label": "YES",
        "outcome1Price": 0.72,
        "outcome2Id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "outcome2Label": "NO",
        "outcome2Price": 0.28,
        "yesBuyPrice": 0.72,
        "minimumOrderAmount": 1,
        "noBuyPrice": 0.28,
        "feePercentage": 2.0,
        "totalOrders": 843,
        "rules": "Resolves YES if Nigeria qualifies for AFCON 2026.",
    }


@pytest.fixture
def sample_market_with_prop() -> dict:
    return {
        "id": "f6a7b8c9-d0e1-2345-fabc-678901234567",
        "title": "Manchester City to Win",
        "status": "open",
        "outcome1Id": "01234567-89ab-cdef-0123-456789abcdef",
        "outcome1Label": "YES",
        "outcome1Price": 0.63,
        "outcome2Id": "fedcba98-7654-3210-fedc-ba9876543210",
        "outcome2Label": "NO",
        "outcome2Price": 0.37,
        "propLine": 1.5,
        "propDirection": "OVER",
        "propTeam": {
            "id": "team-uuid-1",
            "name": "Manchester City FC",
            "slug": "manchester-city-fc",
            "league": "England - Premier League",
            "sport": "SOCCER",
        },
        "yesBuyPrice": 0.63,
        "noBuyPrice": 0.37,
        "feePercentage": 0.5,
        "totalOrders": 420,
        "rules": "Resolves YES if Manchester City wins the match.",
    }


@pytest.fixture
def sample_market_with_reward() -> dict:
    return {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "title": "Will Super Eagles qualify?",
        "status": "open",
        "outcome1Id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "outcome1Label": "YES",
        "outcome1Price": 0.72,
        "outcome2Id": "d4e5f6a7-b8c9-0123-defa-234567890123",
        "outcome2Label": "NO",
        "outcome2Price": 0.28,
        "liquidityReward": {
            "rewardPool": 5000,
            "maxSpreadCents": 5,
            "minNotionalOrderSize": 10.0,
        },
    }


@pytest.fixture
def sample_simple_event() -> dict:
    return {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "slug": "super-eagles-afcon-2026",
        "title": "Will Super Eagles qualify for AFCON 2026?",
        "description": "Nigeria national football team qualification.",
        "category": "sports",
        "type": "single",
        "engine": "AMM",
        "status": "open",
        "resolutionDate": "2025-11-20T00:00:00Z",
        "closingDate": "2025-11-19T18:00:00Z",
        "imageUrl": "https://cdn.bayse.markets/events/afcon2026.jpg",
        "liquidity": 50000,
        "totalVolume": 120000,
        "totalOrders": 843,
        "supportedCurrencies": ["USD", "NGN"],
        "userWatchlisted": False,
        "markets": [
            {
                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "title": "Will Super Eagles qualify?",
                "status": "open",
                "outcome1Id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "outcome1Label": "YES",
                "outcome1Price": 0.72,
                "outcome2Id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "outcome2Label": "NO",
                "outcome2Price": 0.28,
                "yesBuyPrice": 0.72,
                "minimumOrderAmount": 1,
                "noBuyPrice": 0.28,
                "feePercentage": 2.0,
                "totalOrders": 843,
                "rules": "Resolves YES if Nigeria qualifies for AFCON 2026.",
            }
        ],
    }


@pytest.fixture
def sample_crypto_event() -> dict:
    return {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "slug": "crypto-btc-1h-feb-24-11am",
        "title": "Bitcoin Hourly — Feb 24 11am GMT",
        "category": "crypto",
        "type": "single",
        "engine": "AMM",
        "status": "open",
        "openingDate": "2025-02-24T11:00:00Z",
        "closingDate": "2025-02-24T12:00:00Z",
        "resolutionDate": "2025-02-24T12:01:00Z",
        "assetSymbolPair": "BTCUSDT",
        "eventThreshold": 96250.50,
        "seriesSlug": "crypto-btc-1h",
        "liquidity": 10000,
        "totalVolume": 25000,
        "totalOrders": 142,
        "supportedCurrencies": ["USD", "NGN"],
        "userWatchlisted": False,
        "markets": [
            {
                "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                "title": "BTC above $96,250.50?",
                "status": "open",
                "outcome1Id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "outcome1Label": "YES",
                "outcome1Price": 0.55,
                "outcome2Id": "d4e5f6a7-b8c9-0123-defa-234567890123",
                "outcome2Label": "NO",
                "outcome2Price": 0.45,
                "yesBuyPrice": 0.55,
                "noBuyPrice": 0.45,
                "feePercentage": 2.0,
                "totalOrders": 142,
                "marketThreshold": 96250.50,
                "rules": "Resolves YES if BTC price is above $96,250.50 at closing.",
            }
        ],
    }


@pytest.fixture
def sample_combined_event() -> dict:
    return {
        "id": "e5f6a7b8-c9d0-1234-efab-cd567890abcd",
        "slug": "mci-vs-avl-2026-05-24",
        "title": "Manchester City vs Aston Villa",
        "description": "Premier League match",
        "category": "sports",
        "type": "combined",
        "engine": "CLOB",
        "status": "open",
        "sportMarketType": "TEAM_H2H_3WAY",
        "sportGameId": "game-12345",
        "sportGameSlug": "bm-game-20260524-mci-avl",
        "resolutionDate": "2026-05-24T20:00:00Z",
        "closingDate": "2026-05-24T15:00:00Z",
        "imageUrl": "https://cdn.bayse.markets/events/mci-avl.jpg",
        "liquidity": 75000,
        "totalVolume": 250000,
        "totalOrders": 1250,
        "supportedCurrencies": ["USD"],
        "userWatchlisted": True,
        "markets": [
            {
                "id": "f6a7b8c9-d0e1-2345-fabc-678901234567",
                "title": "Manchester City to Win",
                "status": "open",
                "outcome1Id": "01234567-89ab-cdef-0123-456789abcdef",
                "outcome1Label": "YES",
                "outcome1Price": 0.63,
                "outcome2Id": "fedcba98-7654-3210-fedc-ba9876543210",
                "outcome2Label": "NO",
                "outcome2Price": 0.37,
                "propTeam": {
                    "id": "team-uuid-1",
                    "name": "Manchester City FC",
                    "slug": "manchester-city-fc",
                    "league": "England - Premier League",
                    "sport": "SOCCER",
                },
                "yesBuyPrice": 0.63,
                "noBuyPrice": 0.37,
                "feePercentage": 0.5,
                "totalOrders": 420,
                "rules": "Resolves YES if Manchester City wins the match.",
            },
            {
                "id": "a7b8c9d0-e1f2-3456-abcd-789012345678",
                "title": "Aston Villa to Win",
                "status": "open",
                "outcome1Id": "12345678-9abc-def0-1234-56789abcdef0",
                "outcome1Label": "YES",
                "outcome1Price": 0.63,
                "outcome2Id": "0fedcba9-8765-4321-0fed-cba987654321",
                "outcome2Label": "NO",
                "outcome2Price": 0.37,
                "propTeam": {
                    "id": "team-uuid-2",
                    "name": "Aston Villa FC",
                    "slug": "aston-villa-fc",
                    "league": "England - Premier League",
                    "sport": "SOCCER",
                },
                "yesBuyPrice": 0.63,
                "noBuyPrice": 0.37,
                "feePercentage": 0.5,
                "totalOrders": 420,
                "rules": "Resolves YES if Aston Villa wins the match.",
            },
            {
                "id": "b8c9d0e1-f234-5678-bcde-890123456789",
                "title": "Draw",
                "status": "open",
                "outcome1Id": "23456789-abcd-ef01-2345-6789abcdef01",
                "outcome1Label": "YES",
                "outcome1Price": 0.63,
                "outcome2Id": "1fedcba9-8765-4321-1fed-cba987654321",
                "outcome2Label": "NO",
                "outcome2Price": 0.37,
                "propTeam": None,
                "yesBuyPrice": 0.63,
                "noBuyPrice": 0.37,
                "feePercentage": 0.5,
                "totalOrders": 420,
                "rules": "Resolves YES if match ends in a draw.",
            },
        ],
    }


@pytest.fixture
def sample_list_response(sample_simple_event: dict, sample_crypto_event: dict) -> dict:
    return {
        "events": [sample_simple_event, sample_crypto_event],
        "pagination": {
            "page": 1,
            "size": 10,
            "lastPage": 3,
            "totalCount": 28,
        },
    }


@pytest.fixture
def sample_series() -> dict:
    return {
        "id": "f1e2d3c4-b5a6-7890-abcd-ef1234567890",
        "slug": "crypto-btc-1h",
        "displayName": "Bitcoin Hourly Markets",
        "description": "Bitcoin price prediction markets that run every hour.",
        "category": "CRYPTO",
        "intervalType": "HOURLY",
        "assetSymbol": "BTC",
        "automationType": "CRYPTO_PRICE_UP_DOWN_HOURLY",
    }


@pytest.fixture
def sample_series_list_response(sample_series: dict) -> dict:
    return {
        "series": [
            sample_series,
            {
                "id": "e2d3c4b5-a697-8901-bcde-f12345678901",
                "slug": "crypto-eth-1d",
                "displayName": "Ethereum Daily Markets",
                "description": "Ethereum price prediction markets that run daily.",
                "category": "CRYPTO",
                "intervalType": "DAILY",
                "assetSymbol": "ETH",
                "automationType": "CRYPTO_PRICE_UP_DOWN_DAILY",
            },
        ],
        "pagination": {
            "page": 1,
            "size": 20,
            "lastPage": 1,
            "totalCount": 12,
        },
    }
