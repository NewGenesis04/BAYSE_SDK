from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Activity(BaseModel):
    """A single account activity entry."""

    id: str
    type: str
    description: str | None = None
    amount: float | None = None
    currency: str | None = None
    eventId: str | None = None
    marketId: str | None = None
    createdAt: datetime
