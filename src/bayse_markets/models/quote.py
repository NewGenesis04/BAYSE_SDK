from __future__ import annotations

from pydantic import BaseModel, Field


class Quote(BaseModel):
    """A quote for a potential trade without committing to it."""

    cost: float
    shares: float
    fees: float
    price: float | None = None
    profit_estimate: float | None = Field(default=None, alias="profitEstimate")
    currency: str | None = None
