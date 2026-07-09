from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    """Pagination metadata returned by list endpoints."""

    page: int
    size: int
    last_page: int = Field(alias="lastPage")
    total_count: int = Field(alias="totalCount")


class PaginatedResponse[DataT](BaseModel):
    """Generic wrapper for paginated list responses."""

    data: list[DataT]
    pagination: PaginationMeta


class Outcome(StrEnum):
    """Represents a market outcome string.

    Typical values are ``"YES"`` / ``"NO"`` for binary markets,
    but can be any string for multi-outcome markets.
    """

    YES = "YES"
    NO = "NO"

    @classmethod
    def _missing_(cls, value: object) -> Outcome | None:
        """Allow arbitrary outcome strings without breaking."""
        return None


class Currency(StrEnum):
    """Supported trading currencies."""

    USD = "USD"
    NGN = "NGN"


class MarketEngine(StrEnum):
    """Market engine type."""

    AMM = "AMM"
    CLOB = "CLOB"


class MarketType(StrEnum):
    """Event type."""

    SINGLE = "single"
    MULTI = "multi"


class Side(StrEnum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"
