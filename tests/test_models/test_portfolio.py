from __future__ import annotations

from bayse_markets.models.portfolio import PortfolioResponse


class TestPortfolioModel:
    """Tests for the full-tree portfolio response model."""

    def test_parse_full_tree(self, sample_portfolio_response: dict) -> None:
        portfolio = PortfolioResponse.model_validate(sample_portfolio_response)

        assert portfolio.portfolioCost == 100
        assert portfolio.portfolioCurrentValue == 107.60
        assert len(portfolio.outcomeBalances) == 1

        balance = portfolio.outcomeBalances[0]
        assert balance.outcome == "YES"
        assert balance.balance == 138.21
        assert balance.market.title == "Will Super Eagles qualify?"
        assert balance.market.event.title == "Will Super Eagles qualify for AFCON 2026?"
        assert balance.market.event.type == "single"

    def test_pagination_is_parsed(self, sample_portfolio_response: dict) -> None:
        portfolio = PortfolioResponse.model_validate(sample_portfolio_response)
        assert portfolio.pagination.page == 1
        assert portfolio.pagination.totalCount == 1

    def test_round_trip(self, sample_portfolio_response: dict) -> None:
        portfolio = PortfolioResponse.model_validate(sample_portfolio_response)
        serialised = portfolio.model_dump(mode="json")
        PortfolioResponse.model_validate(serialised)

    def test_empty_balances(self) -> None:
        data = {
            "outcomeBalances": [],
            "portfolioCost": 0,
            "portfolioCurrentValue": 0,
            "portfolioPercentageChange": 0,
            "pagination": {"page": 1, "size": 20, "lastPage": 1, "totalCount": 0},
        }
        portfolio = PortfolioResponse.model_validate(data)
        assert portfolio.outcomeBalances == []
