from __future__ import annotations

from pydantic import BaseModel, Field


class Asset(BaseModel):
    """A wallet asset (currency balance)."""

    currency: str
    balance: float
    available_balance: float = Field(alias="availableBalance")
