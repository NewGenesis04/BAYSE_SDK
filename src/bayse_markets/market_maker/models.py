from __future__ import annotations

from pydantic import BaseModel, Field


class MintRequest(BaseModel):
    """Request body for ``POST /v1/pm/markets/{marketId}/mint``."""

    quantity: float = Field(..., gt=0, description="Wallet amount to spend in the selected currency")
    currency: str = Field(default="USD", description="Currency code (USD or NGN)")


class MintResponse(BaseModel):
    """Response from ``POST /v1/pm/markets/{marketId}/mint``."""

    operationId: str
    marketId: str
    quantity: float
    outcome1Price: float
    outcome2Price: float


class BurnRequest(BaseModel):
    """Request body for ``POST /v1/pm/markets/{marketId}/burn``."""

    quantity: float = Field(..., gt=0, description="Amount to redeem in the selected currency")
    currency: str = Field(default="USD", description="Currency code (USD or NGN)")


class BurnResponse(BaseModel):
    """Response from ``POST /v1/pm/markets/{marketId}/burn``."""

    operationId: str
    marketId: str
    quantity: float
    outcome1Price: float
    outcome2Price: float
    proceeds: float
