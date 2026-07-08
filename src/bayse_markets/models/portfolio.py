from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

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
    outcomeId: str
    balance: float
    availableBalance: float
    averagePrice: float
    cost: float
    currentValue: float
    sellPrice: float
    payoutIfOutcomeWins: float
    percentageChange: float
    currency: str
    market: PortfolioMarket
    createdAt: datetime
    updatedAt: datetime


class PortfolioResponse(BaseModel):
    """Full portfolio response (non-standard pagination — nested inside body)."""

    outcomeBalances: list[OutcomeBalance]
    portfolioCost: float
    portfolioCurrentValue: float
    portfolioPercentageChange: float
    pagination: PaginationMeta
