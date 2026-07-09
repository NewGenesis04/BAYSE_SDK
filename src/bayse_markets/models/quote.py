from __future__ import annotations

from pydantic import BaseModel, Field


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
