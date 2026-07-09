from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Ticker(BaseModel):
    """Market ticker with 24h statistics."""

    market_id: str = Field(alias="marketId")
    outcome: str
    last_price: float = Field(alias="lastPrice")
    best_bid: float = Field(alias="bestBid")
    best_ask: float = Field(alias="bestAsk")
    mid_price: float = Field(alias="midPrice")
    spread: float
    volume_24h: float = Field(alias="volume24h")
    high_24h: float = Field(alias="high24h")
    low_24h: float = Field(alias="low24h")
    price_change_24h: float = Field(alias="priceChange24h")
    trade_count_24h: int = Field(alias="tradeCount24h")
    timestamp: datetime
