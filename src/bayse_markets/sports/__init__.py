"""Sports data: leagues, teams, and games.

Sports endpoints are **read-only** and do not require authentication.
Order mechanics for sports markets route through the main client.
"""

from bayse_markets.sports._client import SportsClient

__all__ = ["SportsClient"]
