from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QuoteRequest(BaseModel):
    """Request body for getting a price quote."""

    model_config = ConfigDict(populate_by_name=True)

    side: str
    outcome_id: str = Field(alias="outcomeId")
    amount: float
    currency: str = "USD"


class Quote(BaseModel):
    """A quote for a potential trade without committing to it."""

    price: float
    current_market_price: float = Field(alias="currentMarketPrice")
    quantity: float
    amount: float
    cost_of_shares: float = Field(alias="costOfShares")
    fee: float
    price_impact_absolute: float = Field(alias="priceImpactAbsolute")
    profit_percentage: float | None = Field(default=None, alias="profitPercentage")
    currency_base_multiplier: float = Field(alias="currencyBaseMultiplier")
    complete_fill: bool = Field(alias="completeFill")
    trade_goes_over_max_liability: bool = Field(alias="tradeGoesOverMaxLiability")
