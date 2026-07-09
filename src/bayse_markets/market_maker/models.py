from __future__ import annotations

from pydantic import BaseModel, Field


class MintRequest(BaseModel):
    """Request body for ``POST /v1/pm/markets/{marketId}/mint``."""

    quantity: float = Field(..., gt=0, description="Wallet amount to spend in the selected currency")
    currency: str = Field(default="USD", description="Currency code (USD or NGN)")


class MintResponse(BaseModel):
    """Response from ``POST /v1/pm/markets/{marketId}/mint``."""

    operation_id: str = Field(alias="operationId")
    market_id: str = Field(alias="marketId")
    quantity: float
    outcome1_price: float = Field(alias="outcome1Price")
    outcome2_price: float = Field(alias="outcome2Price")


class BurnRequest(BaseModel):
    """Request body for ``POST /v1/pm/markets/{marketId}/burn``."""

    quantity: float = Field(..., gt=0, description="Amount to redeem in the selected currency")
    currency: str = Field(default="USD", description="Currency code (USD or NGN)")


class BurnResponse(BaseModel):
    """Response from ``POST /v1/pm/markets/{marketId}/burn``."""

    operation_id: str = Field(alias="operationId")
    market_id: str = Field(alias="marketId")
    quantity: float
    outcome1_price: float = Field(alias="outcome1Price")
    outcome2_price: float = Field(alias="outcome2Price")
    proceeds: float
