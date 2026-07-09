from __future__ import annotations

import pytest

from bayse_markets.market_maker.models import BurnRequest, BurnResponse, MintRequest, MintResponse


class TestMintResponseModel:
    """Tests for the MintResponse model."""

    def test_parse(self, sample_mint_response: dict) -> None:
        resp = MintResponse.model_validate(sample_mint_response)
        assert resp.operation_id == "d4e5f6a7-b8c9-0123-defa-456789012345"
        assert resp.market_id == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        assert resp.quantity == 10
        assert resp.outcome1_price == 0.65
        assert resp.outcome2_price == 0.35

    def test_round_trip(self, sample_mint_response: dict) -> None:
        resp = MintResponse.model_validate(sample_mint_response)
        serialised = resp.model_dump(mode="json", by_alias=True)
        MintResponse.model_validate(serialised)


class TestBurnResponseModel:
    """Tests for the BurnResponse model."""

    def test_parse(self, sample_burn_response: dict) -> None:
        resp = BurnResponse.model_validate(sample_burn_response)
        assert resp.operation_id == "e5f6a7b8-c9d0-1234-efab-567890123456"
        assert resp.market_id == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        assert resp.quantity == 10
        assert resp.outcome1_price == 0.65
        assert resp.outcome2_price == 0.35
        assert resp.proceeds == 10.00

    def test_round_trip(self, sample_burn_response: dict) -> None:
        resp = BurnResponse.model_validate(sample_burn_response)
        serialised = resp.model_dump(mode="json", by_alias=True)
        BurnResponse.model_validate(serialised)


class TestMintRequestModel:
    """Tests for the MintRequest model."""

    def test_default_currency(self) -> None:
        req = MintRequest(quantity=50)
        assert req.quantity == 50
        assert req.currency == "USD"

    def test_custom_currency(self) -> None:
        req = MintRequest(quantity=100, currency="NGN")
        assert req.currency == "NGN"

    def test_quantity_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="greater than"):
            MintRequest(quantity=0)


class TestBurnRequestModel:
    """Tests for the BurnRequest model."""

    def test_default_currency(self) -> None:
        req = BurnRequest(quantity=25)
        assert req.quantity == 25
        assert req.currency == "USD"

    def test_quantity_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="greater than"):
            BurnRequest(quantity=-1)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_mint_response() -> dict:
    return {
        "operationId": "d4e5f6a7-b8c9-0123-defa-456789012345",
        "marketId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "quantity": 10,
        "outcome1Price": 0.65,
        "outcome2Price": 0.35,
    }


@pytest.fixture
def sample_burn_response() -> dict:
    return {
        "operationId": "e5f6a7b8-c9d0-1234-efab-567890123456",
        "marketId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "quantity": 10,
        "outcome1Price": 0.65,
        "outcome2Price": 0.35,
        "proceeds": 10.00,
    }
