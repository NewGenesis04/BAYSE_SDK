from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response from the health check endpoint."""

    status: str


class VersionResponse(BaseModel):
    """Response from the version endpoint."""

    version: str = Field(alias="version")
