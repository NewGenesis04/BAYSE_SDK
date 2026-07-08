from __future__ import annotations

from pydantic import BaseModel


class Quote(BaseModel):
    """A quote for a potential trade without committing to it."""

    cost: float
    shares: float
    fees: float
    price: float | None = None
    profitEstimate: float | None = None
    currency: str | None = None
