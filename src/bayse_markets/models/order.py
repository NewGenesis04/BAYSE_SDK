from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Order(BaseModel):
    """A prediction market order."""

    id: str
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    side: str
    outcome: str
    amount: float
    currency: str
    price: float | None = None
    status: str
    filled_amount: float | None = Field(default=None, alias="filledAmount")
    remaining_amount: float | None = Field(default=None, alias="remainingAmount")
    type: str | None = None
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    metadata: dict[str, Any] = Field(default_factory=dict)
