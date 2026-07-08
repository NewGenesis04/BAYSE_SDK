from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Ticker(BaseModel):
    """Market ticker with 24h statistics."""

    marketId: str
    outcome: str
    lastPrice: float
    bestBid: float
    bestAsk: float
    midPrice: float
    spread: float
    volume24h: float
    high24h: float
    low24h: float
    priceChange24h: float
    tradeCount24h: int
    timestamp: datetime
