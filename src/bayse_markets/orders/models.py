from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OrderRequest(BaseModel):
    """Base order request.

    Schema is provisional — will be updated as the API is explored.
    """

    side: str
    outcome: str
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    type: str | None = None
    price: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LimitOrder(OrderRequest):
    """A limit order with a specific price."""

    type: str = "LIMIT"  # type: ignore[assignment]
    price: float = Field(..., gt=0)


class MarketOrder(OrderRequest):
    """A market order (fills at best available price)."""

    type: str = "MARKET"  # type: ignore[assignment]
