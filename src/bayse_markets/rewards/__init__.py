"""Liquidity rewards: track epoch payouts and active accumulation.

Requires read authentication (``X-Public-Key`` header).
"""

from bayse_markets.rewards._client import LiquidityRewardsClient

__all__ = ["LiquidityRewardsClient"]
