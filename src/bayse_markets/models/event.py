from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EventMarket(BaseModel):
    """A market within an event."""

    id: str
    title: str


class Event(BaseModel):
    """A prediction market event."""

    id: str
    title: str
    status: str
    type: str | None = None
    engine: str | None = None
    markets: list[EventMarket] = Field(default_factory=list)
    liquidityReward: Any = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    startsAt: datetime | None = None
    endsAt: datetime | None = None
    resolvesAt: datetime | None = None
