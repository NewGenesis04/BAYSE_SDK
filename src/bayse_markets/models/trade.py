from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from bayse_markets.models._shared import PaginationMeta


class Trade(BaseModel):
    """A single trade execution (CLOB match)."""

    id: str
    market_id: str = Field(alias="marketId")
    size: float
    taker_user_id: str = Field(alias="takerUserId")
    maker_user_id: str = Field(alias="makerUserId")
    taker_order_id: str = Field(alias="takerOrderId")
    maker_order_id: str = Field(alias="makerOrderId")
    taker_fee: float = Field(alias="takerFee")
    maker_outcome_id: str = Field(alias="makerOutcomeId")
    taker_outcome_id: str = Field(alias="takerOutcomeId")
    match_type: str = Field(alias="matchType")
    taker_side: str = Field(alias="takerSide")
    taker_price: float = Field(alias="takerPrice")
    maker_price: float = Field(alias="makerPrice")
    created_at: datetime = Field(alias="createdAt")


class ListTradesResponse(BaseModel):
    """Wrapper for the paginated trades list response."""

    data: list[Trade]
    pagination: PaginationMeta
