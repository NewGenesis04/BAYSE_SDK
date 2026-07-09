from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from bayse_markets.models._shared import PaginationMeta


class Activity(BaseModel):
    """A single account activity entry."""

    id: str
    type: str
    event_id: str = Field(alias="eventId")
    market_id: str = Field(alias="marketId")
    outcome_id: str = Field(alias="outcomeId")
    order_id: str | None = Field(default=None, alias="orderId")
    settlement_id: str | None = Field(default=None, alias="settlementId")
    transaction_id: str | None = Field(default=None, alias="transactionId")
    event_type: str = Field(alias="eventType")
    image_url: str | None = Field(default=None, alias="imageUrl")
    event_title: str = Field(alias="eventTitle")
    market_title: str = Field(alias="marketTitle")
    outcome: str | None = None
    resolved_outcome: str | None = Field(default=None, alias="resolvedOutcome")
    currency: str
    amount: float = 0.0
    fee: float = 0.0
    size: float = 0.0
    filled_size: float | None = Field(default=None, alias="filledSize")
    remaining_size: float | None = Field(default=None, alias="remainingSize")
    price: float = 0.0
    avg_fill_price: float | None = Field(default=None, alias="avgFillPrice")
    total_cost: float = Field(default=0.0, alias="totalCost")
    currency_base_multiplier: float = Field(default=1.0, alias="currencyBaseMultiplier")
    status: str | None = None
    expires_at: str | None = Field(default=None, alias="expiresAt")
    payout: float | None = Field(default=None, alias="payout")
    amount_spent: float | None = Field(default=None, alias="amountSpent")
    amount_refunded: float | None = Field(default=None, alias="amountRefunded")
    amount_earned: float | None = Field(default=None, alias="amountEarned")
    shares_returned: float | None = Field(default=None, alias="sharesReturned")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")

    @field_validator(
        "amount",
        "fee",
        "size",
        "filled_size",
        "remaining_size",
        "price",
        "avg_fill_price",
        "total_cost",
        "currency_base_multiplier",
        "payout",
        "amount_spent",
        "amount_refunded",
        "amount_earned",
        "shares_returned",
        mode="before",
    )
    @classmethod
    def parse_float_string(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            return float(v)
        return v


class ListActivitiesResponse(BaseModel):
    activities: list[Activity]
    pagination: PaginationMeta
