from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from bayse_markets.models._shared import PaginationMeta


class Trade(BaseModel):
    """A single trade execution."""

    id: str
    market_id: str = Field(alias="marketId")
    outcome: str
    price: float
    size: float
    created_at: datetime = Field(alias="createdAt")


class ListTradesResponse(BaseModel):
    """Wrapper for the paginated trades list response.

    The API uses a nested ``data`` key for the trade list.
    """

    data: list[Trade]
    pagination: PaginationMeta
