from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient
from bayse_markets.market_maker.models import BurnResponse, MintResponse


async def mint_shares(
    client: BayseClient,
    market_id: str,
    *,
    quantity: float,
    currency: str = "USD",
    trace_id: str | None = None,
) -> BayseResponse[MintResponse]:
    """Mint YES+NO share pairs for a market.

    Deposits funds and receives an equal number of YES and NO shares.
    Does not affect market prices.

    Args:
        client: An open ``BayseClient`` instance.
        market_id: UUID of the target market.
        quantity: Wallet amount to spend in the selected currency.
        currency: ``USD`` (default) or ``NGN``.
        trace_id: Optional trace ID override.

    Returns:
        ``BayseResponse`` wrapping the mint result.

    Warning:
        This is a **market maker** operation. Minting creates complete
        sets (YES+NO pairs). Most users should use the order book instead.
    """
    resp = await client._request(
        "POST",
        f"/v1/pm/markets/{market_id}/mint",
        body={"quantity": quantity, "currency": currency},
        auth_level="write",
        trace_id=trace_id,
    )
    parsed = MintResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def burn_shares(
    client: BayseClient,
    market_id: str,
    *,
    quantity: float,
    currency: str = "USD",
    trace_id: str | None = None,
) -> BayseResponse[BurnResponse]:
    """Burn YES+NO share pairs for a market.

    Destroys equal YES and NO shares and receives funds back.
    Does not affect market prices.

    Args:
        client: An open ``BayseClient`` instance.
        market_id: UUID of the target market.
        quantity: Amount to redeem in the selected currency.
        currency: ``USD`` (default) or ``NGN``.
        trace_id: Optional trace ID override.

    Returns:
        ``BayseResponse`` wrapping the burn result.

    Warning:
        This is a **market maker** operation. Burning destroys complete
        sets (YES+NO pairs). You must hold sufficient shares of both
        outcomes. Most users should use the order book instead.
    """
    resp = await client._request(
        "POST",
        f"/v1/pm/markets/{market_id}/burn",
        body={"quantity": quantity, "currency": currency},
        auth_level="write",
        trace_id=trace_id,
    )
    parsed = BurnResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )
