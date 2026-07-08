from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LiquidityReward(BaseModel):
    """A completed epoch payout."""

    epochId: str
    marketId: str
    rewardPool: float
    userShare: float
    payout: float
    currency: str
    epochStart: datetime
    epochEnd: datetime
    paidAt: datetime


class ActiveLiquidityReward(BaseModel):
    """In-progress epoch accumulation with estimated payouts."""

    marketId: str
    rewardPool: float
    estimatedShare: float
    estimatedPayout: float
    currency: str
    epochStart: datetime
    epochEnd: datetime
    samplesSoFar: int
