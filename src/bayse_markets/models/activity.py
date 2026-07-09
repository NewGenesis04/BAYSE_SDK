from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Activity(BaseModel):
    """A single account activity entry."""

    id: str
    type: str
    description: str | None = None
    amount: float | None = None
    currency: str | None = None
    event_id: str | None = Field(default=None, alias="eventId")
    market_id: str | None = Field(default=None, alias="marketId")
    created_at: datetime = Field(alias="createdAt")
