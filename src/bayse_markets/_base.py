from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


@dataclass
class BayseResponse[T]:
    """Wrapper for every successful API response."""

    status_code: int
    data: T
    timestamp: datetime
    headers: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata returned by list endpoints."""

    page: int
    size: int
    lastPage: int
    totalCount: int


DataT = TypeVar("DataT")


class PaginatedResponse[DataT](BaseModel):
    """Generic wrapper for paginated list responses."""

    data: list[DataT]
    pagination: PaginationMeta
