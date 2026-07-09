from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PnlBreakdownItem(BaseModel):
    event_id: str = Field(alias="eventId")
    event_title: str = Field(alias="eventTitle")
    realized_pnl: float = Field(alias="realizedPnl")
    currency: str
    last_activity: datetime = Field(alias="lastActivity")


class PnLResponse(BaseModel):
    realized_pnl: float = Field(alias="realizedPnl")
    realized_pnl_percent: float = Field(alias="realizedPnlPercent")
    settlement_pnl: float = Field(alias="settlementPnl")
    trade_pnl: float = Field(alias="tradePnl")
    wins: int
    losses: int
    currency: str
    breakdown: list[PnlBreakdownItem] | None = None
