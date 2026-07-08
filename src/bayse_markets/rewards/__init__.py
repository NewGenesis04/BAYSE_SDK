"""Liquidity rewards: track epoch payouts and active accumulation.

Requires read authentication (``X-Public-Key`` header).

Usage:

    from bayse_markets.rewards import list_rewards, get_active_rewards

    payouts = await list_rewards(client, page=1, size=20)
    active = await get_active_rewards(client)
"""

from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient


async def list_rewards(
    client: BayseClient,
    *,
    page: int = 1,
    size: int = 20,
    trace_id: str | None = None,
) -> BayseResponse[dict]:
    """Get paginated history of completed epoch payouts.

    Args:
        client: An open ``BayseClient`` instance.
        page: Page number (default 1).
        size: Items per page (default 20).
        trace_id: Optional trace ID override.

    Returns:
        Response containing paginated reward payout history.
    """
    return await client._request(
        "GET",
        "/v1/pm/liquidity-rewards",
        params={"page": page, "size": size},
        auth_level="read",
        trace_id=trace_id,
    )


async def get_active_rewards(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[dict]:
    """Get in-progress accumulation with estimated payouts.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID override.

    Returns:
        Response containing active reward estimates.
    """
    return await client._request(
        "GET",
        "/v1/pm/liquidity-rewards/active",
        auth_level="read",
        trace_id=trace_id,
    )


__all__ = [
    "list_rewards",
    "get_active_rewards",
]
