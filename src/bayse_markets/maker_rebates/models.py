from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from bayse_markets.models._shared import PaginationMeta


class MakerRebate(BaseModel):
    """A completed maker rebate epoch payout."""

    epoch_id: str = Field(alias="epochId")
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    maker_volume: float = Field(alias="makerVolume")
    trade_count: int = Field(alias="tradeCount")
    rebate_amount: float = Field(alias="rebateAmount")
    is_paid: bool = Field(alias="isPaid")
    epoch_start: datetime = Field(alias="epochStart")
    epoch_end: datetime = Field(alias="epochEnd")
    status: str


class ActiveMakerRebate(BaseModel):
    """In-progress maker rebate accumulation."""

    epoch_id: str = Field(alias="epochId")
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    maker_volume: float = Field(alias="makerVolume")
    trade_count: int = Field(alias="tradeCount")
    rebate_amount: float = Field(alias="rebateAmount")
    epoch_start: datetime = Field(alias="epochStart")
    epoch_end: datetime = Field(alias="epochEnd")


class ListMakerRebatesResponse(BaseModel):
    """Wrapper for the paginated maker rebates list response."""

    data: list[MakerRebate] | None = None
    pagination: PaginationMeta | None = None


class ActiveMakerRebatesResponse(BaseModel):
    """Wrapper for the active maker rebates response."""

    data: list[ActiveMakerRebate]
