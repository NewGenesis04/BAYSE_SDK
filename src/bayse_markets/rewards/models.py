from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LiquidityReward(BaseModel):
    """A completed epoch payout."""

    epoch_id: str = Field(alias="epochId")
    market_id: str = Field(alias="marketId")
    reward_pool: float = Field(alias="rewardPool")
    user_share: float = Field(alias="userShare")
    payout: float
    currency: str
    epoch_start: datetime = Field(alias="epochStart")
    epoch_end: datetime = Field(alias="epochEnd")
    paid_at: datetime = Field(alias="paidAt")


class ActiveLiquidityReward(BaseModel):
    """In-progress epoch accumulation with estimated payouts."""

    market_id: str = Field(alias="marketId")
    reward_pool: float = Field(alias="rewardPool")
    estimated_share: float = Field(alias="estimatedShare")
    estimated_payout: float = Field(alias="estimatedPayout")
    currency: str
    epoch_start: datetime = Field(alias="epochStart")
    epoch_end: datetime = Field(alias="epochEnd")
    samples_so_far: int = Field(alias="samplesSoFar")
