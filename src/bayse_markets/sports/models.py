from __future__ import annotations

from pydantic import BaseModel


class SportsLeague(BaseModel):
    """A sports league."""

    id: str
    name: str
    sport: str | None = None
    country: str | None = None


class SportsTeam(BaseModel):
    """A sports team."""

    id: str
    name: str
    abbreviation: str | None = None
    leagueId: str | None = None
    logoUrl: str | None = None


class SportsGame(BaseModel):
    """A sports game/match."""

    id: str
    leagueId: str
    homeTeamId: str
    awayTeamId: str
    homeTeamName: str | None = None
    awayTeamName: str | None = None
    startTime: str | None = None
    status: str | None = None
    homeScore: int | None = None
    awayScore: int | None = None
