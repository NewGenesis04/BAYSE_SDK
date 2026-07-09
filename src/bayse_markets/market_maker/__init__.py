"""Market maker operations: mint and burn shares.

.. warning::
    Minting and burning are **market-maker-level operations**.
    They deposit or withdraw complete sets of YES+NO shares.
    Only use these if you understand the mechanics of
    prediction market liquidity provision.

    If you are a regular trader, use the order book instead.
"""

from bayse_markets.market_maker._api import burn_shares, mint_shares
from bayse_markets.market_maker.models import BurnRequest, BurnResponse, MintRequest, MintResponse

__all__ = [
    "burn_shares",
    "BurnRequest",
    "BurnResponse",
    "mint_shares",
    "MintRequest",
    "MintResponse",
]
