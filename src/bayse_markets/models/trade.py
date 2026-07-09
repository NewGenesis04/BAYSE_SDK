from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Trade(BaseModel):
    """A single trade execution."""

    id: str
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    outcome: str
    side: str
    price: float
    amount: float
    currency: str
    timestamp: datetime
