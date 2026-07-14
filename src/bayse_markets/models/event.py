from __future__ import annotations

from datetime import datetime

from typing import Any

from pydantic import BaseModel, Field, field_validator

from bayse_markets.models._shared import PaginationMeta


class PropTeam(BaseModel):
    id: str
    name: str
    slug: str
    league: str
    sport: str


class MarketLiquidityReward(BaseModel):
    reward_pool: float = Field(alias="rewardPool")
    max_spread_cents: int = Field(alias="maxSpreadCents")
    min_notional_order_size: float = Field(alias="minNotionalOrderSize")


class EventMarket(BaseModel):
    id: str
    title: str
    status: str | None = None
    outcome1_id: str | None = Field(default=None, alias="outcome1Id")
    outcome1_label: str | None = Field(default=None, alias="outcome1Label")
    outcome1_price: float | None = Field(default=None, alias="outcome1Price")
    outcome2_id: str | None = Field(default=None, alias="outcome2Id")
    outcome2_label: str | None = Field(default=None, alias="outcome2Label")
    outcome2_price: float | None = Field(default=None, alias="outcome2Price")
    resolved_outcome_id: str | None = Field(default=None, alias="resolvedOutcomeId")
    yes_buy_price: float | None = Field(default=None, alias="yesBuyPrice")
    no_buy_price: float | None = Field(default=None, alias="noBuyPrice")
    minimum_order_amount: float | None = Field(default=None, alias="minimumOrderAmount")
    fee_percentage: float | None = Field(default=None, alias="feePercentage")
    total_orders: int | None = Field(default=None, alias="totalOrders")
    rules: str | None = None
    market_threshold: float | None = Field(default=None, alias="marketThreshold")
    market_threshold_range: str | None = Field(default=None, alias="marketThresholdRange")
    market_close_value: float | None = Field(default=None, alias="marketCloseValue")
    prop_line: float | None = Field(default=None, alias="propLine")
    prop_direction: str | None = Field(default=None, alias="propDirection")
    prop_team: PropTeam | None = Field(default=None, alias="propTeam")
    liquidity_reward: MarketLiquidityReward | None = Field(default=None, alias="liquidityReward")


class Event(BaseModel):
    id: str
    title: str
    status: str
    slug: str | None = None
    description: str | None = None
    category: str | None = None
    type: str | None = None
    engine: str | None = None
    opening_date: datetime | None = Field(default=None, alias="openingDate")
    resolution_date: datetime | None = Field(default=None, alias="resolutionDate")
    closing_date: datetime | None = Field(default=None, alias="closingDate")
    image_url: str | None = Field(default=None, alias="imageUrl")
    liquidity: float | None = None
    total_volume: float | None = Field(default=None, alias="totalVolume")
    total_orders: int | None = Field(default=None, alias="totalOrders")
    supported_currencies: list[str] | None = Field(default=None, alias="supportedCurrencies")
    user_watchlisted: bool | None = Field(default=None, alias="userWatchlisted")
    series_slug: str | None = Field(default=None, alias="seriesSlug")
    sport_game_id: str | None = Field(default=None, alias="sportGameId")
    sport_game_slug: str | None = Field(default=None, alias="sportGameSlug")
    sport_market_type: str | None = Field(default=None, alias="sportMarketType")
    asset_symbol_pair: str | None = Field(default=None, alias="assetSymbolPair")
    event_threshold: float | None = Field(default=None, alias="eventThreshold")
    event_threshold_range: str | None = Field(default=None, alias="eventThresholdRange")
    event_close_value: float | None = Field(default=None, alias="eventCloseValue")
    markets: list[EventMarket] = Field(default_factory=list)

    @field_validator("opening_date", "resolution_date", "closing_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v


class ListEventsResponse(BaseModel):
    events: list[Event]
    pagination: PaginationMeta


class EventSeries(BaseModel):
    id: str
    slug: str
    display_name: str = Field(alias="displayName")
    description: str | None = None
    category: str | None = None
    interval_type: str | None = Field(default=None, alias="intervalType")
    asset_symbol: str | None = Field(default=None, alias="assetSymbol")
    automation_type: str | None = Field(default=None, alias="automationType")
    icon_url: str | None = Field(default=None, alias="iconUrl")


class ListEventSeriesResponse(BaseModel):
    series: list[EventSeries]
    pagination: PaginationMeta


class LeanEvent(BaseModel):
    id: str
    title: str
    opening_date: datetime | None = Field(default=None, alias="openingDate")
    closing_date: datetime | None = Field(default=None, alias="closingDate")
    resolution_date: datetime | None = Field(default=None, alias="resolutionDate")

    @field_validator("opening_date", "resolution_date", "closing_date", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: Any) -> Any:
        if v == "":
            return None
        return v
