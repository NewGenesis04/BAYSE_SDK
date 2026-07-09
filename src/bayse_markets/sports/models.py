from __future__ import annotations

from pydantic import BaseModel, Field


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
    league_id: str | None = Field(default=None, alias="leagueId")
    logo_url: str | None = Field(default=None, alias="logoUrl")


class SportsGame(BaseModel):
    """A sports game/match."""

    id: str
    league_id: str = Field(alias="leagueId")
    home_team_id: str = Field(alias="homeTeamId")
    away_team_id: str = Field(alias="awayTeamId")
    home_team_name: str | None = Field(default=None, alias="homeTeamName")
    away_team_name: str | None = Field(default=None, alias="awayTeamName")
    start_time: str | None = Field(default=None, alias="startTime")
    status: str | None = None
    home_score: int | None = Field(default=None, alias="homeScore")
    away_score: int | None = Field(default=None, alias="awayScore")
