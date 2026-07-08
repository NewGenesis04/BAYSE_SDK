from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Order(BaseModel):
    """A prediction market order."""

    id: str
    eventId: str
    marketId: str
    side: str
    outcome: str
    amount: float
    currency: str
    price: float | None = None
    status: str
    filledAmount: float | None = None
    remainingAmount: float | None = None
    type: str | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
