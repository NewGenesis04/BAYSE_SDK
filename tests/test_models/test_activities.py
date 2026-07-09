from __future__ import annotations

from datetime import datetime

import pytest

from bayse_markets.models.activity import Activity, ListActivitiesResponse


class TestActivityModel:
    """Tests for the Activity model."""

    def test_parse_full(self, sample_activity: dict) -> None:
        act = Activity.model_validate(sample_activity)
        assert act.id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert act.type == "BUY_MARKET_ORDER_CREATED"
        assert act.event_title == "Will BTC reach $100k by March 2026?"
        assert act.market_title == "Bitcoin Price Prediction"
        assert act.outcome == "YES"
        assert act.amount == 100.0
        assert act.fee == 2.0
        assert act.size == 138.21
        assert act.price == 0.7235
        assert act.total_cost == 102.0
        assert act.currency_base_multiplier == 1.0
        assert act.status == "FILLED"
        assert isinstance(act.created_at, datetime)

    def test_string_amounts_parsed_as_floats(self) -> None:
        data = {
            "id": "abc",
            "type": "BUY_TRADE_FILL",
            "eventId": "evt_1",
            "marketId": "mkt_1",
            "outcomeId": "out_1",
            "eventType": "SINGLE",
            "eventTitle": "Test Event",
            "marketTitle": "Test Market",
            "currency": "USD",
            "amount": "50.50",
            "fee": "1.00",
            "size": "75.25",
            "price": "0.50",
            "totalCost": "51.50",
            "currencyBaseMultiplier": "1",
            "createdAt": "2026-02-17T12:00:00Z",
        }
        act = Activity.model_validate(data)
        assert act.amount == 50.50
        assert act.fee == 1.00
        assert act.size == 75.25
        assert act.price == 0.50
        assert act.total_cost == 51.50
        assert act.currency_base_multiplier == 1.0

    def test_nullable_string_amounts(self) -> None:
        data = {
            "id": "abc",
            "type": "BUY_LIMIT_ORDER_CREATED",
            "eventId": "evt_1",
            "marketId": "mkt_1",
            "outcomeId": "out_1",
            "eventType": "SINGLE",
            "eventTitle": "Test",
            "marketTitle": "Test",
            "currency": "USD",
            "amount": "100",
            "fee": "0",
            "size": "0",
            "price": "0.70",
            "totalCost": "100",
            "currencyBaseMultiplier": "1",
            "createdAt": "2026-02-17T12:00:00Z",
        }
        act = Activity.model_validate(data)
        assert act.filled_size is None
        assert act.avg_fill_price is None
        assert act.payout is None

    def test_round_trip(self, sample_activity: dict) -> None:
        act = Activity.model_validate(sample_activity)
        serialised = act.model_dump(mode="json", by_alias=True, exclude_none=True)
        Activity.model_validate(serialised)


class TestListActivitiesResponse:
    """Tests for the ListActivitiesResponse model."""

    def test_parse(self, sample_activity_list: dict) -> None:
        resp = ListActivitiesResponse.model_validate(sample_activity_list)
        assert len(resp.activities) == 1
        assert resp.pagination.page == 1
        assert resp.pagination.total_count == 73

    def test_round_trip(self, sample_activity_list: dict) -> None:
        resp = ListActivitiesResponse.model_validate(sample_activity_list)
        serialised = resp.model_dump(mode="json", by_alias=True, exclude_none=True)
        ListActivitiesResponse.model_validate(serialised)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_activity() -> dict:
    return {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "type": "BUY_MARKET_ORDER_CREATED",
        "eventId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "marketId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "outcomeId": "d4e5f6a7-b8c9-0123-def1-234567890123",
        "orderId": "e5f6a7b8-c9d0-1234-ef12-345678901234",
        "eventType": "SINGLE",
        "imageUrl": "https://example.com/image.png",
        "eventTitle": "Will BTC reach $100k by March 2026?",
        "marketTitle": "Bitcoin Price Prediction",
        "outcome": "YES",
        "currency": "USD",
        "amount": "100",
        "fee": "2",
        "size": "138.21",
        "price": "0.7235",
        "totalCost": "102",
        "currencyBaseMultiplier": "1",
        "status": "FILLED",
        "createdAt": "2026-02-17T12:00:00Z",
        "updatedAt": "2026-02-17T12:00:00Z",
    }


@pytest.fixture
def sample_activity_list(sample_activity: dict) -> dict:
    return {
        "activities": [sample_activity],
        "pagination": {
            "page": 1,
            "size": 20,
            "lastPage": 4,
            "totalCount": 73,
        },
    }
