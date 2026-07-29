from __future__ import annotations

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from bayse_markets.models._shared import PaginationMeta


class PlaceOrderRequest(BaseModel):
    """Request body for placing an order."""

    model_config = ConfigDict(populate_by_name=True)

    side: str
    outcome_id: str = Field(alias="outcomeId")
    amount: float
    order_type: str = Field(alias="type")
    currency: str = "USD"
    price: float | None = None
    time_in_force: str | None = Field(default=None, alias="timeInForce")
    post_only: bool | None = Field(default=None, alias="postOnly")
    stp_mode: str | None = Field(default=None, alias="stpMode")
    max_slippage: float | None = Field(default=None, alias="maxSlippage")
    expires_at: str | None = Field(default=None, alias="expiresAt")


class Order(BaseModel):
    """A prediction market order, as returned by the order-read routes."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    market_id: str = Field(alias="marketId")
    outcome_id: str = Field(alias="outcomeId")
    """UUID of the outcome. The wire key is ``outcomeId`` on this route."""
    side: str
    order_type: str = Field(alias="type")
    stp_mode: str = Field(alias="stpMode")
    status: str
    amount: float
    price: float
    size: float
    filled_size: float = Field(alias="filledSize")
    remaining_size: float = Field(alias="remainingSize")
    avg_fill_price: float | None = Field(default=None, alias="avgFillPrice")
    fee: float | None = None
    currency: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PlacedOrder(BaseModel):
    """An order returned by place-order or batch endpoints.
    Covers both AMM and CLOB engine shapes — all fields optional.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    outcome_id: str | None = Field(default=None, alias="outcome")
    """UUID of the outcome.

    The wire key here is ``outcome`` — not ``outcomeId`` as on the read routes —
    but the value is the same outcome UUID. ``api-reference.md`` documents this
    field as a ``YES``/``NO`` label; a live placement on 2026-07-29 returned a UUID,
    so the docs are wrong, not the model.
    """
    side: str | None = None
    type: str | None = None
    status: str | None = None
    amount: float | None = None
    price: float | None = None
    quantity: float | None = None
    currency: str | None = None
    market_id: str | None = Field(default=None, alias="marketId")
    user_id: str | None = Field(default=None, alias="userId")
    order_type: str | None = Field(default=None, alias="orderType")
    size: float | None = None
    filled_size: float | None = Field(default=None, alias="filledSize")
    remaining_size: float | None = Field(default=None, alias="remainingSize")
    avg_fill_price: float | None = Field(default=None, alias="avgFillPrice")
    fee: float | None = None
    post_only: bool | None = Field(default=None, alias="postOnly")
    stp_mode: str | None = Field(default=None, alias="stpMode")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class PlaceOrderResponse(BaseModel):
    """Response from placing a single order."""
    model_config = ConfigDict(populate_by_name=True)

    engine: str
    order: PlacedOrder | None = Field(
        default=None,
        validation_alias=AliasChoices("clobOrder", "ammOrder", "order"),
    )


class CancelOrderResponse(BaseModel):
    """Response from cancelling a single order."""

    message: str


class ListOrdersResponse(BaseModel):
    """Wrapper for the paginated orders list response."""

    orders: list[Order]
    pagination: PaginationMeta


class BatchOrderError(BaseModel):
    """Per-item error in a batch response."""

    code: str
    message: str


class BatchSummary(BaseModel):
    """Summary counts for a batch operation."""

    total: int
    succeeded: int
    failed: int


class BatchPlaceResult(BaseModel):
    """A single result item from a batch place response."""

    index: int
    client_order_id: str | None = Field(default=None, alias="clientOrderId")
    success: bool
    order: PlacedOrder | None = None
    error: BatchOrderError | None = None


class BatchPlaceResponse(BaseModel):
    """Response from batch order placement."""

    engine: str
    results: list[BatchPlaceResult]
    summary: BatchSummary


class BatchAmendResult(BaseModel):
    """A single result item from a batch amend response."""

    index: int
    order_id: str = Field(alias="orderId")
    success: bool
    order: PlacedOrder | None = None
    error: BatchOrderError | None = None


class BatchAmendResponse(BaseModel):
    """Response from batch order amendment."""

    engine: str
    results: list[BatchAmendResult]
    summary: BatchSummary


class BatchCancelResult(BaseModel):
    """A single result item from a batch cancel response."""

    order_id: str = Field(alias="orderId")
    success: bool
    error: BatchOrderError | None = None


class BatchCancelResponse(BaseModel):
    """Response from batch order cancellation."""

    engine: str
    results: list[BatchCancelResult]
    summary: BatchSummary
