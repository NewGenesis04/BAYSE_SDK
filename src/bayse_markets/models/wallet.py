from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AssetAddress(BaseModel):
    """A deposit address for an asset."""

    id: str
    address: str
    symbol: str
    provider: str
    network: str


class Asset(BaseModel):
    """A wallet asset (currency balance)."""

    id: str
    symbol: str
    user_id: str = Field(alias="userId")
    network: str
    available_balance: float = Field(alias="availableBalance")
    pending_balance: float = Field(alias="pendingBalance")
    deposit_activity: str = Field(alias="depositActivity")
    withdrawal_activity: str = Field(alias="withdrawalActivity")
    wager_activity: str = Field(alias="wagerActivity")
    is_default: bool = Field(alias="isDefault")
    is_local_currency_asset: bool = Field(alias="isLocalCurrencyAsset")
    addresses: list[AssetAddress] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ListAssetsResponse(BaseModel):
    """Wrapper for the wallet assets response."""

    assets: list[Asset]
