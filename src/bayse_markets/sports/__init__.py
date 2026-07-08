"""Sports data: leagues, teams, and games.

Sports endpoints are **read-only** and do not require authentication.
Order mechanics for sports markets route through the main client.

Usage:

    from bayse_markets.sports import list_leagues, list_teams, list_games

    leagues = await list_leagues(client)
"""

from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient


async def list_leagues(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[dict]:
    """List all sports leagues.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID override.

    Returns:
        Response containing a list of sports leagues.
    """
    return await client._request(
        "GET",
        "/v1/pm/sports/leagues",
        auth_level="public",
        trace_id=trace_id,
    )


async def list_teams(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[dict]:
    """List all sports teams.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID override.

    Returns:
        Response containing a list of sports teams.
    """
    return await client._request(
        "GET",
        "/v1/pm/sports/teams",
        auth_level="public",
        trace_id=trace_id,
    )


async def list_games(
    client: BayseClient,
    *,
    params: dict | None = None,
    trace_id: str | None = None,
) -> BayseResponse[dict]:
    """List sports games with optional filters.

    Args:
        client: An open ``BayseClient`` instance.
        params: Optional query parameters (e.g. league, date).
        trace_id: Optional trace ID override.

    Returns:
        Response containing a list of sports games.
    """
    return await client._request(
        "GET",
        "/v1/pm/sports/games",
        params=params,
        auth_level="public",
        trace_id=trace_id,
    )


__all__ = [
    "list_leagues",
    "list_teams",
    "list_games",
]
