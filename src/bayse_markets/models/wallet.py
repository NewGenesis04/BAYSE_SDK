from __future__ import annotations

from pydantic import BaseModel


class Asset(BaseModel):
    """A wallet asset (currency balance)."""

    currency: str
    balance: float
    availableBalance: float
