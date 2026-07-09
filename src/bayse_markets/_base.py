from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TypeVar

T = TypeVar("T")


@dataclass
class BayseResponse[T]:
    """Wrapper for every successful API response."""

    status_code: int
    data: T
    timestamp: datetime
    headers: dict[str, str] = field(default_factory=dict)
    trace_id: str | None = None
