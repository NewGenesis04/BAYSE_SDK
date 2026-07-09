from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from bayse_markets.models._shared import PaginationMeta


class SportsLeague(BaseModel):
    """A sports league."""

    name: str
    key: str
    short_name: str = Field(alias="shortName")
    image_url: str = Field(alias="imageUrl")


class SportsTeam(BaseModel):
    """A sports team."""

    id: str
    sport: str
    name: str
    slug: str
    short_code: str = Field(alias="shortCode")
    league: str
    image_url: str | None = Field(default=None, alias="imageUrl")
    is_popular: bool = Field(alias="isPopular")


class GameTeam(BaseModel):
    """Team details nested inside a sports game."""

    id: str
    sport: str
    name: str
    slug: str
    short_code: str = Field(alias="shortCode")
    league: str
    image_url: str | None = Field(default=None, alias="imageUrl")
    is_popular: bool = Field(alias="isPopular")


class SportsGame(BaseModel):
    """A sports game/match."""

    id: str
    slug: str
    sport: str
    home_team_id: str = Field(alias="homeTeamId")
    away_team_id: str = Field(alias="awayTeamId")
    start_date: datetime = Field(alias="startDate")
    status: str
    is_live: bool = Field(alias="isLive")
    is_popular: bool = Field(alias="isPopular")
    league: str
    home_team: GameTeam = Field(alias="homeTeam")
    away_team: GameTeam = Field(alias="awayTeam")


class ListLeaguesResponse(BaseModel):
    """Wrapper for the sports leagues list response."""

    leagues: list[SportsLeague]


class ListTeamsResponse(BaseModel):
    """Wrapper for the paginated sports teams list response."""

    teams: list[SportsTeam]
    pagination: PaginationMeta


class ListGamesResponse(BaseModel):
    """Wrapper for the paginated sports games list response."""

    games: list[SportsGame]
    pagination: PaginationMeta
