from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from bayse_markets.models._shared import PaginationMeta


class LiquidityReward(BaseModel):
    """A completed liquidity reward epoch payout."""

    epoch_id: str = Field(alias="epochId")
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    accumulated_shares: float = Field(alias="accumulatedShares")
    sample_count: int = Field(alias="sampleCount")
    payout: float
    is_paid: bool = Field(alias="isPaid")
    epoch_start: datetime = Field(alias="epochStart")
    epoch_end: datetime = Field(alias="epochEnd")
    status: str


class ActiveLiquidityReward(BaseModel):
    """In-progress liquidity reward accumulation."""

    epoch_id: str = Field(alias="epochId")
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    accumulated_shares: float = Field(alias="accumulatedShares")
    sample_count: int = Field(alias="sampleCount")
    estimated_payout: float = Field(alias="estimatedPayout")
    epoch_start: datetime = Field(alias="epochStart")
    epoch_end: datetime = Field(alias="epochEnd")


class ListRewardsResponse(BaseModel):
    """Wrapper for the paginated liquidity rewards list response."""

    data: list[LiquidityReward] | None = None
    pagination: PaginationMeta | None = None


class ActiveRewardsResponse(BaseModel):
    """Wrapper for the active liquidity rewards response."""

    data: list[ActiveLiquidityReward]
