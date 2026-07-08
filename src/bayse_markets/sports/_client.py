from __future__ import annotations

from bayse_markets._base import BayseResponse
from bayse_markets._client import BayseClient


class SportsClient:
    """Convenience wrapper around sports endpoints.

    All sports endpoints are public (no auth required).
    """

    def __init__(self, client: BayseClient) -> None:
        self._client = client

    async def list_leagues(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[dict]:
        """List all sports leagues."""
        return await self._client.list_sports_leagues(trace_id=trace_id)

    async def list_teams(
        self,
        *,
        trace_id: str | None = None,
    ) -> BayseResponse[dict]:
        """List all sports teams."""
        return await self._client.list_sports_teams(trace_id=trace_id)

    async def list_games(
        self,
        *,
        params: dict | None = None,
        trace_id: str | None = None,
    ) -> BayseResponse[dict]:
        """List sports games with optional filters."""
        return await self._client.list_sports_games(params=params, trace_id=trace_id)
