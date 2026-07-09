from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PricePoint(BaseModel):
    outcome: str
    price: float
    timestamp: datetime
