# Bayse Markets Python SDK

Async Python SDK for the [Bayse Markets](https://docs.bayse.markets) prediction market API.

```python
import asyncio
from bayse_markets import BayseClient

async def main():
    async with BayseClient(
        public_key="pk_live_...",
        secret_key="sk_live_...",
        env="production",
    ) as client:
        events = await client.list_events(page=1, size=10)
        for event in events.data:
            print(event["title"])

asyncio.run(main())
```

## Install

```bash
pip install bayse-markets
# or
uv add bayse-markets
```

## Requirements

- Python 3.12+
- `httpx`
- `pydantic>=2.0`

## Quick start

### Get a portfolio

```python
portfolio = await client.get_portfolio()
for balance in portfolio.data["outcomeBalances"]:
    print(f"{balance['market']['title']}: {balance['outcome']} = {balance['balance']}")
```

### Place an order

```python
result = await client.place_order(
    event_id="evt_123",
    market_id="mkt_456",
    body={
        "side": "BUY",
        "outcome": "YES",
        "amount": 1000,
        "currency": "NGN",
    },
)
```

### Sports leagues

```python
from bayse_markets.sports import list_leagues

leagues = await list_leagues(client)
for league in leagues.data:
    print(league["name"])
```

### Mint shares (market maker)

```python
from bayse_markets.market_maker import mint_shares

result = await mint_shares(
    client,
    market_id="mkt_456",
    quantity=100,
    currency="USD",
)
```

## Documentation

Full documentation is available at [docs.bayse.markets](https://docs.bayse.markets).

## License

Proprietary.
