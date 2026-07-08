from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from bayse_markets._client import BayseClient


@pytest.fixture
def public_key() -> str:
    return "pk_test_abc123"


@pytest.fixture
def secret_key() -> str:
    return "sk_test_secret456"


@pytest.fixture
async def client(public_key: str, secret_key: str) -> AsyncGenerator[BayseClient, None]:
    """Create a BayseClient with a mocked HTTP transport."""
    async with BayseClient(
        public_key=public_key,
        secret_key=secret_key,
        env="production",
    ) as c:
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.headers = {"x-trace-id": "test-000001"}
        mock_http.request.return_value = mock_response
        c._http = mock_http
        yield c


@pytest.fixture
def sample_portfolio_response() -> dict:
    return {
        "outcomeBalances": [
            {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "outcome": "YES",
                "outcomeId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "balance": 138.21,
                "availableBalance": 138.21,
                "averagePrice": 0.7235,
                "cost": 100,
                "currentValue": 107.60,
                "sellPrice": 0.7786,
                "payoutIfOutcomeWins": 138.21,
                "percentageChange": 7.60,
                "currency": "USD",
                "market": {
                    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                    "title": "Will Super Eagles qualify?",
                    "event": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "title": "Will Super Eagles qualify for AFCON 2026?",
                        "type": "single",
                        "engine": "AMM",
                    },
                },
                "createdAt": "2026-02-17T12:00:00Z",
                "updatedAt": "2026-02-17T12:05:00Z",
            }
        ],
        "portfolioCost": 100,
        "portfolioCurrentValue": 107.60,
        "portfolioPercentageChange": 7.60,
        "pagination": {"page": 1, "size": 20, "lastPage": 1, "totalCount": 1},
    }


@pytest.fixture
def sample_ticker_response() -> dict:
    return {
        "marketId": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "outcome": "YES",
        "lastPrice": 0.72,
        "bestBid": 0.70,
        "bestAsk": 0.72,
        "midPrice": 0.71,
        "spread": 0.02,
        "volume24h": 15420,
        "high24h": 0.74,
        "low24h": 0.65,
        "priceChange24h": 0.04,
        "tradeCount24h": 247,
        "timestamp": "2026-02-17T12:00:00Z",
    }
