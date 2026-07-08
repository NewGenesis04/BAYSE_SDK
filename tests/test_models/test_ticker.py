from __future__ import annotations

from bayse_markets.models.ticker import Ticker


class TestTickerModel:
    """Tests for the ticker response model."""

    def test_parse_ticker(self, sample_ticker_response: dict) -> None:
        ticker = Ticker.model_validate(sample_ticker_response)

        assert ticker.marketId == "b2c3d4e5-f6a7-8901-bcde-f12345678901"
        assert ticker.outcome == "YES"
        assert ticker.lastPrice == 0.72
        assert ticker.bestBid == 0.70
        assert ticker.bestAsk == 0.72
        assert ticker.midPrice == 0.71
        assert ticker.spread == 0.02
        assert ticker.volume24h == 15420
        assert ticker.high24h == 0.74
        assert ticker.low24h == 0.65
        assert ticker.priceChange24h == 0.04
        assert ticker.tradeCount24h == 247

    def test_round_trip(self, sample_ticker_response: dict) -> None:
        ticker = Ticker.model_validate(sample_ticker_response)
        serialised = ticker.model_dump(mode="json")
        Ticker.model_validate(serialised)
