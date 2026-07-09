from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from bayse_markets.models._shared import PaginationMeta


class PortfolioMarketEvent(BaseModel):
    """Event nested inside a portfolio market."""

    id: str
    title: str
    type: str | None = None
    engine: str | None = None


class PortfolioMarket(BaseModel):
    """Market nested inside an outcome balance."""

    id: str
    title: str
    event: PortfolioMarketEvent


class OutcomeBalance(BaseModel):
    """A single outcome position in the portfolio."""

    id: str
    outcome: str
    outcome_id: str = Field(alias="outcomeId")
    balance: float
    available_balance: float = Field(alias="availableBalance")
    average_price: float = Field(alias="averagePrice")
    cost: float
    current_value: float = Field(alias="currentValue")
    sell_price: float = Field(alias="sellPrice")
    payout_if_outcome_wins: float = Field(alias="payoutIfOutcomeWins")
    percentage_change: float = Field(alias="percentageChange")
    currency: str
    market: PortfolioMarket
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PortfolioResponse(BaseModel):
    """Full portfolio response (non-standard pagination — nested inside body)."""

    outcome_balances: list[OutcomeBalance] = Field(alias="outcomeBalances")
    portfolio_cost: float = Field(alias="portfolioCost")
    portfolio_current_value: float = Field(alias="portfolioCurrentValue")
    portfolio_percentage_change: float = Field(alias="portfolioPercentageChange")
    pagination: PaginationMeta
