"""Sports data: leagues, teams, and games.

Sports endpoints are **read-only** and do not require authentication.
Order mechanics for sports markets route through the main client.

Usage:

    from bayse_markets.sports import list_leagues, list_teams, list_games

    leagues = await list_leagues(client)
"""

from __future__ import annotations

from typing import Any

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient
from bayse_markets.sports.models import ListGamesResponse, ListLeaguesResponse, ListTeamsResponse


async def list_leagues(
    client: BayseClient,
    *,
    trace_id: str | None = None,
) -> BayseResponse[ListLeaguesResponse]:
    """List all sports leagues.

    Args:
        client: An open ``BayseClient`` instance.
        trace_id: Optional trace ID override.

    Returns:
        Response containing a list of sports leagues.
    """
    resp = await client._request(
        "GET",
        "/v1/pm/sports/leagues",
        auth_level="public",
        trace_id=trace_id,
    )
    parsed = ListLeaguesResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def list_teams(
    client: BayseClient,
    *,
    league: str | None = None,
    sport: str | None = None,
    page: int = 1,
    size: int = 50,
    trace_id: str | None = None,
) -> BayseResponse[ListTeamsResponse]:
    """List sports teams, optionally filtered by league or sport.

    Args:
        client: An open ``BayseClient`` instance.
        league: Filter by league name (e.g. ``"England - Premier League"``).
        sport: Filter by sport (e.g. ``"soccer"``).
        page: Page number (default 1).
        size: Results per page, max 100 (default 50).
        trace_id: Optional trace ID override.

    Returns:
        Response containing a paginated list of sports teams.
    """
    params: dict[str, Any] = {"page": page, "size": size}
    if league is not None:
        params["league"] = league
    if sport is not None:
        params["sport"] = sport

    resp = await client._request(
        "GET",
        "/v1/pm/sports/teams",
        params=params,
        auth_level="public",
        trace_id=trace_id,
    )
    parsed = ListTeamsResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


async def list_games(
    client: BayseClient,
    *,
    league: str | None = None,
    sport: str | None = None,
    page: int = 1,
    size: int = 50,
    trace_id: str | None = None,
) -> BayseResponse[ListGamesResponse]:
    """List sports games, optionally filtered by league or sport.

    Args:
        client: An open ``BayseClient`` instance.
        league: Filter by league name (e.g. ``"England - Premier League"``).
        sport: Filter by sport (e.g. ``"soccer"``).
        page: Page number (default 1).
        size: Results per page, max 100 (default 50).
        trace_id: Optional trace ID override.

    Returns:
        Response containing a paginated list of sports games.
    """
    params: dict[str, Any] = {"page": page, "size": size}
    if league is not None:
        params["league"] = league
    if sport is not None:
        params["sport"] = sport

    resp = await client._request(
        "GET",
        "/v1/pm/sports/games",
        params=params,
        auth_level="public",
        trace_id=trace_id,
    )
    parsed = ListGamesResponse.model_validate(resp.data)
    return BayseResponse(
        status_code=resp.status_code,
        data=parsed,
        timestamp=resp.timestamp,
        headers=resp.headers,
        trace_id=resp.trace_id,
    )


__all__ = [
    "list_leagues",
    "list_teams",
    "list_games",
]
