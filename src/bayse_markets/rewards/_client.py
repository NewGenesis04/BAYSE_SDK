from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient


class LiquidityRewardsClient:
    """Convenience wrapper around liquidity rewards endpoints.

    Requires read authentication (``X-Public-Key`` header).
    """

    def __init__(self, client: BayseClient) -> None:
        self._client = client

    async def list_rewards(
        self,
        *,
        page: int = 1,
        size: int = 20,
        trace_id: str | None = None,
    ) -> BayseResponse[dict]:
        """Get paginated history of completed epoch payouts."""
        return await self._client.list_liquidity_rewards(page=page, size=size, trace_id=trace_id)

    async def get_active(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[dict]:
        """Get in-progress accumulation with estimated payouts."""
        return await self._client.get_active_liquidity_rewards(trace_id=trace_id)
