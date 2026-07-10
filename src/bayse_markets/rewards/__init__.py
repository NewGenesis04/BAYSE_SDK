from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient
from bayse_markets.rewards.models import ActiveRewardsResponse, ListRewardsResponse


async def list_rewards(
    client: BayseClient,
    *,
    page: int = 1,
    size: int = 20,
    trace_id: str | None = None,
) -> BayseResponse[ListRewardsResponse]:
    """Get paginated history of completed liquidity reward epoch payouts.

    Args:
        client: An open ``BayseClient`` instance.
        page: Page number (default 1).
        size: Items per page (default 20).
        trace_id: Optional trace ID for request correlation.

    Returns:
        Response containing paginated reward payout history.
    """
    resp = await client._request(
        "GET",
        "/v1/pm/liquidity-rewards",
        params={"page": page, "size": size},
        auth_level="read",
        trace_id=trace_id,
    )
    parsed = ListRewardsResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def get_active_rewards(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[ActiveRewardsResponse]:
    """Get in-progress liquidity reward accumulation across active epochs.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID for request correlation.

    Returns:
        Response containing active reward estimates.
    """
    resp = await client._request(
        "GET",
        "/v1/pm/liquidity-rewards/active",
        auth_level="read",
        trace_id=trace_id,
    )
    parsed = ActiveRewardsResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


__all__ = [
    "list_rewards",
    "get_active_rewards",
]
