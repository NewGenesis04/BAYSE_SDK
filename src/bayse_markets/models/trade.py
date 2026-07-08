from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Trade(BaseModel):
    """A single trade execution."""

    id: str
    eventId: str
    marketId: str
    outcome: str
    side: str
    price: float
    amount: float
    currency: str
    timestamp: datetime
