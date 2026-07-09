from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OrderBookLevel(BaseModel):
    price: float
    quantity: float
    total: float


class OrderBook(BaseModel):
    market_id: str = Field(alias="marketId")
    outcome_id: str = Field(alias="outcomeId")
    timestamp: datetime
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    last_traded_price: float | None = Field(default=None, alias="lastTradedPrice")
    last_traded_side: str | None = Field(default=None, alias="lastTradedSide")
