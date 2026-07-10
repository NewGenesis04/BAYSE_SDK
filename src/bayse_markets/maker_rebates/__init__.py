from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient
from bayse_markets.maker_rebates.models import (
    ActiveMakerRebatesResponse,
    ListMakerRebatesResponse,
)


async def list_maker_rebates(
    client: BayseClient,
    *,
    page: int = 1,
    size: int = 20,
    trace_id: str | None = None,
) -> BayseResponse[ListMakerRebatesResponse]:
    """Get paginated history of completed maker rebate epoch payouts.

    Args:
        client: An open ``BayseClient`` instance.
        page: Page number (default 1).
        size: Items per page (default 20).
        trace_id: Optional trace ID for request correlation.

    Returns:
        Response containing paginated rebate payout history.
    """
    resp = await client._request(
        "GET",
        "/v1/pm/maker-rebates",
        params={"page": page, "size": size},
        auth_level="read",
        trace_id=trace_id,
    )
    parsed = ListMakerRebatesResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def get_active_maker_rebates(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[ActiveMakerRebatesResponse]:
    """Get in-progress maker rebate accumulation across active epochs.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID for request correlation.

    Returns:
        Response containing active rebate estimates.
    """
    resp = await client._request(
        "GET",
        "/v1/pm/maker-rebates/active",
        auth_level="read",
        trace_id=trace_id,
    )
    parsed = ActiveMakerRebatesResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


__all__ = [
    "list_maker_rebates",
    "get_active_maker_rebates",
]
