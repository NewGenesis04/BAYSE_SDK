# Bayse Markets Python SDK

Async Python SDK for the [Bayse Markets](https://docs.bayse.markets) prediction market API — fully typed, Pythonic, and covering every endpoint.

```python
from bayse_markets import BayseClient

async with BayseClient(public_key="pk_live_...", secret_key="sk_live_...") as client:
    events = await client.list_events(page=1, size=10)
    for event in events.data.items:
        print(f"{event.title}: {event.close_time}")
```

## Install

```bash
pip install bayse-markets
# or
uv add bayse-markets
```

Requires Python 3.12+.

---

## Key Features

- **100% typed responses** — every endpoint returns `BayseResponse[T]` with proper Pydantic models. No raw dicts.
- **Pythonic field names** — API `camelCase` fields are mapped to `snake_case`. Write `event.close_time`, not `event["closeTime"]`.
- **UserClient** — bootstrap API keys programmatically from email + password. No need to visit the web UI.
- **No auth needed for some endpoints** — price history and order books are public.
- **Full API coverage** — events, orders (single + batch), quoting, portfolio, PnL, trades, activities, wallet, sports, liquidity rewards, maker rebates, market maker, system health.
- **Async only** — built on `httpx` with automatic retries, exponential backoff, and trace IDs.

---

## Quick Start

### Already have API keys

```python
import asyncio
from bayse_markets import BayseClient

async def main():
    async with BayseClient(
        public_key="pk_live_...",
        secret_key="sk_live_...",
    ) as client:
        # Typed responses — use dot access, not dict keys
        pnl = await client.get_pnl(time_period="1M")
        print(f"PnL: {pnl.data.realized_pnl} ({pnl.data.realized_pnl_percent}%)")

        portfolio = await client.get_portfolio()
        for balance in portfolio.data.outcome_balances:
            print(f"{balance.market.title}: {balance.outcome} = {balance.balance}")

        events = await client.list_events(page=1, size=5)
        for event in events.data.items:
            print(f"{event.title} — closes {event.close_time}")

asyncio.run(main())
```

### Don't have keys yet — bootstrap with UserClient

```python
from bayse_markets import UserClient, BayseClient

async with UserClient() as user:
    await user.login("you@example.com", "your-password")
    key = await user.create_api_key("my trading bot")

    # ⚠️ Save these — secret_key is only shown once
    print(f"pk={key.public_key}")
    print(f"sk={key.secret_key}")

    # Now use them with BayseClient
    async with BayseClient(
        public_key=key.public_key,
        secret_key=key.secret_key,
    ) as client:
        wallet = await client.get_assets()
        for asset in wallet.data.assets:
            print(f"Wallet balance: {asset.available_balance}")
        portfolio = await client.get_portfolio()
        print(f"Balance: {portfolio.data.portfolio_current_value}")
```

---

## More Examples

### Place an order

```python
order = await client.place_order(
    event_id="evt_...",
    market_id="mkt_...",
    side="BUY",
    outcome_id="outcome_uuid",
    amount=10000,
    order_type="LIMIT",
    price=0.65,
    currency="NGN",
)
print(f"Order {order.data.order.id} — {order.data.order.status}")
```

### Batch orders

```python
result = await client.batch_place_orders(body={
    "orders": [
        {"marketId": "...", "side": "BUY", "outcome": "YES", "amount": 5000, "price": 0.65},
        {"marketId": "...", "side": "SELL", "outcome": "NO", "amount": 3000, "price": 0.30},
    ]
})
print(f"{result.data.summary.succeeded} placed, {result.data.summary.failed} failed")
```

### Get a quote

```python
quote = await client.get_quote(
    event_id="evt_...",
    market_id="mkt_...",
    side="BUY",
    outcome_id="outcome_uuid",
    amount=500,
    currency="USD",
)
print(f"Price: {quote.data.price}")
```

### Sports

```python
from bayse_markets.sports import list_leagues, list_games

leagues = await list_leagues(client)
for league in leagues.data:
    print(f"{league.name} ({league.sport})")

games = await list_games(client, league="EPL", page=1, size=10)
for game in games.data:
    print(f"{game.home_team.name} vs {game.away_team.name} — {game.start_time}")
```

### Liquidity rewards

```python
from bayse_markets.rewards import list_rewards, get_active_rewards

payouts = await list_rewards(client, page=1, size=20)
for reward in payouts.data.data:
    print(f"Epoch {reward.epoch_id}: {reward.payout} NGN — {'paid' if reward.is_paid else 'pending'}")

    active = await get_active_rewards(client)
    for epoch in active.data.data:
        print(f"Active: {epoch.accumulated_shares} shares → ~{epoch.estimated_payout} NGN")
```

### Maker rebates

```python
from bayse_markets.maker_rebates import list_maker_rebates, get_active_maker_rebates

rebates = await list_maker_rebates(client, page=1, size=20)
for rebate in rebates.data.data:
    print(f"Rebate: {rebate.rebate_amount} NGN — maker volume {rebate.maker_volume}")
```

### Market maker (mint / burn)

```python
from bayse_markets.market_maker import mint_shares, burn_shares

mint = await mint_shares(client, market_id="mkt_...", quantity=100, currency="USD")
print(f"Minted: {mint.data.shares_received} shares")

burn = await burn_shares(client, market_id="mkt_...", quantity=50, currency="USD")
print(f"Burned: {burn.data.cash_received} USD")
```

### Order books

```python
books = await client.get_order_books(
    outcome_ids=["outcome_id_1", "outcome_id_2"],
    depth=5,
)
for book in books.data:
    print(f"Market {book.market_id}: {len(book.bids)} bids, {len(book.asks)} asks")
    if book.last_traded_price:
        print(f"  Last trade: {book.last_traded_price} ({book.last_traded_side})")
```

### Price history

```python
history = await client.get_price_history(
    event_id="evt_...",
    time_period="1W",
    outcome="YES",
)
for market_id, points in history.data.items():
    print(f"Market {market_id}: {len(points)} data points")
    for point in points[:3]:
        print(f"  {point.timestamp}: {point.price}")
```

### Manage API keys (UserClient)

```python
from bayse_markets import UserClient

async with UserClient() as user:
    await user.login("you@example.com", "password")

    keys = await user.list_api_keys()
    for k in keys.keys:
        print(f"{k.name}: {k.public_key} ({k.secret_key_hint})")

    key = await user.create_api_key("new key")
    print(f"Created: {key.public_key} / {key.secret_key}")

    new_key = await user.rotate_api_key(key.id)
    print(f"Rotated: new secret = {new_key.secret_key}")

    await user.revoke_api_key(key.id)
```

### Lookup a user

```python
user = UserClient()
user.public_key = "pk_live_..."
profile = await user.lookup_user(tag="mulumba")
print(f"{profile.tag} — {profile.image_url}")
```

---

## Design Notes

**Typed everywhere.** Every endpoint returns `BayseResponse[T]` where `T` is a Pydantic model. No raw dictionaries, no guesswork about field names. Your editor's autocomplete works.

**Snake_case fields.** The API speaks `camelCase` (`createdAt`, `filledSize`). The SDK translates to `snake_case` (`created_at`, `filled_size`). You can still use the raw API field via `model.model_dump(by_alias=True)` if needed.

**Separate auth domains.** `BayseClient` uses HMAC-signed requests with API keys. `UserClient` uses email/password + session tokens. Two clients, two auth models — no mixing concerns.

**UserClient is a bootstrap tool.** Use it once to create API keys, then never touch it again. `BayseClient` is the permanent workhorse.

**One-time secret keys.** When creating or rotating API keys, the `secret_key` is only returned once. Save it immediately.

---

## Documentation

Full API reference at [docs.bayse.markets](https://docs.bayse.markets).

## License

Proprietary.
