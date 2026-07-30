# Bayse Markets Python SDK

`Python 3.12+` · `MIT`

Async Python SDK for the [Bayse Markets](https://docs.bayse.markets) prediction market API — fully typed, Pythonic, and covering every endpoint.

> This is an independent, community-built SDK by Ogie Omorose — not built, maintained, or endorsed by Bayse.

```python
from bayse_markets import BayseClient

async with BayseClient(public_key="pk_live_...", secret_key="sk_live_...") as client:
    events = await client.list_events(page=1, size=10)
    for event in events.data.events:
        print(f"{event.title}: {event.closing_date}")
```

## Who this is for

- **App developers** building trading bots, dashboards, or integrations on top of Bayse — full order lifecycle (place, batch, amend, cancel), portfolio, wallet, and activity coverage.
- **Data scientists & quantitative researchers** — every response is a Pydantic model that drops straight into `pandas` (see [Data Science Quickstart](#data-science-quickstart)) for backtesting, price history analysis, or signal research.
- **Market makers / liquidity providers** — dedicated `market_maker` (mint/burn), `maker_rebates`, and `rewards` modules for tracking and optimizing liquidity incentives.
- **Anyone bootstrapping API access** — `UserClient` creates and rotates API keys from just an email/password, no dashboard round-trip required.

## Install

```bash
pip install bayse-markets
# or
uv add bayse-markets
```

Requires Python 3.12+.

See [CHANGELOG.md](CHANGELOG.md) for release notes. **0.3.0 adds `buy()` and
`sell()` helpers** — see [Buy & Sell](#buy--sell) below. 0.2.0 contains breaking
changes — if upgrading from 0.1.0, read
[Migrating to 0.2.0](CHANGELOG.md#migrating-to-020).

---

## Configuration

The client works with just two keys, but every knob is adjustable.

```python
from bayse_markets import BayseClient
from bayse_markets._config import Env

async with BayseClient(
    public_key="pk_live_...",
    secret_key="sk_live_...",
    env=Env.SANDBOX,   # or "sandbox" — defaults to production
    timeout=30.0,
) as client:
    ...
```

Retry and trace behaviour are passed as objects:

```python
from bayse_markets._config import RetryConfig, TraceConfig
from bayse_markets._retry import RetryStrategy

client = BayseClient(
    public_key="pk_live_...",
    secret_key="sk_live_...",
    retry_strategy=RetryStrategy(RetryConfig(max_retries=3, base_delay=0.5)),
    trace_config=TraceConfig(session_id="my-bot"),
)
```

<details>
<summary><strong>All configuration fields</strong></summary>

**`BayseClient(...)`**

| Argument | Default | Meaning |
|---|---|---|
| `env` | `Env.PRODUCTION` | `PRODUCTION` → `relay.bayse.markets`, `SANDBOX` → `sandbox.relay.bayse.markets`. Accepts the string `"sandbox"` too. |
| `timeout` | `30.0` | HTTP timeout in seconds. |
| `retry_strategy` | `RetryStrategy(RetryConfig())` | See below. |
| `trace_config` | `TraceConfig()` | See below. |
| `signer` | HMAC-SHA256 | Override only if you need custom request signing. |

**`RetryConfig`**

| Field | Default | Meaning |
|---|---|---|
| `max_retries` | `5` | Attempts after the first. `0` disables retries. |
| `base_delay` | `1.0` | Base for the exponential backoff, in seconds. |
| `max_delay` | `60.0` | Ceiling on any single delay. |
| `jitter` | `0.1` | Random 0–`jitter` seconds added per delay. |
| `retry_on_statuses` | `(429, 500, 502, 503, 504)` | Applied to safe and idempotent requests. |
| `retry_unsafe_on_statuses` | `()` | Applied to non-idempotent requests. Empty by default — see [Reliability & Retries](#reliability--retries). |
| `safe_methods` | `{GET, HEAD, OPTIONS}` | Never has side effects. |
| `idempotent_methods` | `{PUT, DELETE}` | Idempotent by HTTP specification. |

**`TraceConfig`**

| Field | Default | Meaning |
|---|---|---|
| `session_id` | random 12-char hex | Prefix for generated trace IDs. |
| `start_sequence` | `1` | First sequence number. |

</details>

---

## Key Features

- **100% typed responses** — every endpoint returns `BayseResponse[T]` with proper Pydantic models. No raw dicts.
- **Pythonic field names** — API `camelCase` fields are mapped to `snake_case`. Write `event.closing_date`, not `event["closingDate"]`.
- **UserClient** — bootstrap API keys programmatically from email + password. No need to visit the web UI.
- **No auth needed for some endpoints** — price history and order books are public.
- **Full API coverage** — events, orders (single + batch), quoting, portfolio, PnL, trades, activities, wallet, sports, liquidity rewards, maker rebates, market maker, system health.
- **Async only** — built on `httpx` with [method-aware retries](#reliability--retries), exponential backoff, and [trace IDs](#trace-ids). A failed `GET` is replayed; a failed order is not.
- **Retry-safe writes** — the batch endpoints support real, server-verified [idempotency keys](#idempotency).
- **AI-friendly reference** — [`llms.txt`](llms.txt) at the project root gives AI coding tools a condensed, complete reference for using this SDK.

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
        for event in events.data.events:
            print(f"{event.title} — closes {event.closing_date}")

asyncio.run(main())
```

### Don't have keys yet — bootstrap with UserClient

```python
from bayse_markets import UserClient, BayseClient

async with UserClient() as user:
    await user.login("you@example.com", "your-password")
    key = await user.create_api_key("my trading bot")

    # Save these — secret_key is only shown once
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

### Buy & Sell

Two high-level helpers for the most common operations. They call `place_order`
under the hood with the correct `side` and clearer parameter names.

```python
# Buy: spend 10,000 NGN on an outcome
order = await client.buy(
    event_id="evt_...",
    market_id="mkt_...",
    outcome_id="outcome_uuid",
    amount=10000,       # cash spend in the target currency
    order_type="LIMIT",
    price=0.65,
    currency="NGN",
)
print(f"Buy order {order.data.order.id} — {order.data.order.status}")
```

```python
# Sell: liquidate 5.84 shares of an outcome
# event_id / market_id resolved from portfolio automatically
order = await client.sell(
    outcome_id="outcome_uuid",
    shares=5.84,        # share count to sell, NOT cash value
    currency="NGN",
)
print(f"Sell order {order.data.order.id} — {order.data.order.status}")
```

Pass `event_id` and `market_id` explicitly to skip the portfolio lookup:

```python
order = await client.sell(
    event_id="evt_...",
    market_id="mkt_...",
    outcome_id="outcome_uuid",
    shares=5.84,
    currency="NGN",
)
```

### place_order — low-level control

For advanced use cases that need every parameter (e.g. `stp_mode`,
`max_slippage`, `post_only`, `time_in_force`).

**Important:** `amount` has different semantics per side:
- `side="BUY"`: `amount` is the **cash spend** in the target currency.
- `side="SELL"`: `amount` is the **number of shares** to liquidate.

For most use cases, prefer `buy()` or `sell()` — they set the correct side
and name the parameter appropriately.

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
        {
            "marketId": "...", "side": "BUY", "outcomeId": "outcome_uuid_yes",
            "amount": 5000, "type": "LIMIT", "price": 0.65, "currency": "USD",
        },
        {
            "marketId": "...", "side": "SELL", "outcomeId": "outcome_uuid_no",
            "amount": 3000, "type": "LIMIT", "price": 0.30, "currency": "USD",
        },
    ]
})
print(f"{result.data.summary.succeeded} placed, {result.data.summary.failed} failed")
```

> Each order is routed by `outcomeId` alone — `marketId` is accepted but not
> validated, so a mismatched `marketId` won't misroute an order (it's derived
> from the outcome server-side). Don't rely on it as a safety check.

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

## Utilities

Convenience functions that combine or derive data from multiple API calls.
Import from ``bayse_markets.utils``:

```python
from bayse_markets.utils import (
    get_closing_soon,
    get_high_volume_markets,
    get_market_summary,
    get_portfolio_breakdown,
    get_sector_overview,
    compare_outcomes,
    calculate_spread,
)
```

**Find events closing in the next 24 hours:**

```python
closing = await get_closing_soon(client, hours=24, category="sports")
for event in closing.data:
    print(f"{event.title} — closes {event.closing_date}")
```

**Get high-volume events:**

```python
active = await get_high_volume_markets(client, min_volume=100_000)
print(f"{len(active.data)} events above 100k volume")
```

**Consolidated event view (event + all order books):**

```python
summary = await get_market_summary(client, event_id="evt_...")
print(f"{summary.data.event.title}: {len(summary.data.order_books)} order books")
```

**Combined portfolio + wallet:**

```python
bd = await get_portfolio_breakdown(client)
print(f"Portfolio: {bd.data.portfolio_current_value}")
print(f"Wallet assets: {len(bd.data.assets)}")
```

**Compare spreads across outcomes:**

```python
comparisons = await compare_outcomes(
    client, ["outcome_id_1", "outcome_id_2", "outcome_id_3"]
)
for c in comparisons.data:
    print(f"{c.outcome_id}: spread={c.spread}")
```

**Aggregate view of a market sector:**

```python
sector = await get_sector_overview(client, "crypto")
print(f"{sector.data.category}: {sector.data.event_count} events, "
      f"{sector.data.total_volume:.0f} total volume")
```

**Bid-ask spread for a single outcome:**

```python
spread = await calculate_spread(client, "outcome_id")
print(f"Spread: {spread.data.spread} ({spread.data.best_bid} / {spread.data.best_ask})")
```

---

## Data Science Quickstart

Every response is a Pydantic model, so it drops straight into `pandas` with
`model_dump()` — no manual JSON wrangling.

### Events into a DataFrame

```python
import pandas as pd
from bayse_markets import BayseClient

async with BayseClient(public_key=PK, secret_key=SK) as client:
    events = await client.list_events(page=1, size=50, status="open")
    df = pd.DataFrame([e.model_dump() for e in events.data.events])
    print(df[["title", "category", "total_volume", "liquidity"]].sort_values(
        "total_volume", ascending=False
    ).head())
```

### Plot price history with matplotlib

```python
import matplotlib.pyplot as plt
import pandas as pd

history = await client.get_price_history(event_id="evt_...", time_period="1W")

for market_id, points in history.data.items():
    df = pd.DataFrame([p.model_dump() for p in points])
    df.plot(x="timestamp", y="price", title=f"Market {market_id}")

plt.show()
```

### Feed portfolio data into a model

```python
portfolio = await client.get_portfolio()
df = pd.DataFrame([b.model_dump() for b in portfolio.data.outcome_balances])

# e.g. total exposure and unrealized P&L per position, ready for
# whatever sizing/risk logic your strategy uses
df["unrealized_pnl"] = df["current_value"] - df["cost"]
print(df[["outcome", "balance", "cost", "current_value", "unrealized_pnl"]])
```

---

## Logging

The SDK uses Python's standard `logging` module with a `NullHandler` (silent by default).
To inspect SDK internals (requests, retries, trace IDs):

```python
import logging

sdk_logger = logging.getLogger("bayse_markets")
sdk_logger.setLevel(logging.DEBUG)
sdk_logger.addHandler(logging.StreamHandler())
```

Sensitive headers (`authorization`, `x-signature`, `x-public-key`, etc.) are
automatically redacted from log output.

---

## Reliability & Retries

Retries are **method-aware**. A `502` on a `GET` is worth replaying. A `502` on a
`POST /orders` may mean the order was accepted and only the response was lost —
replaying it risks a duplicate. So the SDK does not replay it.

| Request | Retried on |
|---|---|
| `GET` / `HEAD` / `OPTIONS` | `429, 500, 502, 503, 504` |
| `DELETE` / `PUT` | `429, 500, 502, 503, 504` |
| `POST` | **nothing — never retried** |
| `POST` with an `Idempotency-Key` | `429, 500, 502, 503, 504` |

Backoff is exponential with jitter, capped at `max_delay`. Every retry of a
non-idempotent request logs at **WARNING** with the trace ID and attempt number —
it is the one event you want in your scrollback without having enabled debug
logging in advance.

**Why `429` is not retried on a `POST`.** It would be safe only if the rate
limiter sits strictly in front of order acceptance, which no client can verify.
If that assumption is wrong, the cost at the default `max_retries=5` is six live
orders. Opt in if you know your own infrastructure:

```python
RetryConfig(retry_unsafe_on_statuses=(429,))
```

## Idempotency

The batch endpoints accept an `idempotency_key` and the server genuinely
**deduplicates** on it — a replay returns the original result instead of acting
twice. Supplying one re-enables full `5xx` retries for that call.

```python
result = await client.batch_place_orders(
    body={"orders": [{...}]},
    idempotency_key="order-2026-07-29-0001",   # your own unique string
)
```

Verified against production: the same key with an identical body returns the
*original* order id and creates one order; two distinct keys with the same body
create two. The replayed response is indistinguishable from the first — a normal
`200`, not an error.

> **`place_order` and `cancel_order` do not support idempotency keys.** The API
> accepts the header on those routes and silently ignores it, so the SDK does not
> offer the parameter — accepting a key and dropping it would be worse than not
> having one. If you need a retry-safe write, use `batch_place_orders` with a
> batch of one. Otherwise, treat a failed single write as *unresolved* and
> reconcile with `list_orders(currency=...)` before re-sending.

## Trace IDs

Every request carries an `x-trace-id`, auto-generated as
`{session_id}-{sequence:06d}`. Quote it when reporting an issue to Bayse.

```python
resp = await client.list_events(page=1, size=10)
print(resp.trace_id)          # e.g. "77f08ca6d00d-000003"

# Override per call to correlate with your own logs
await client.get_portfolio(trace_id="reconcile-run-42")
```

Pin `session_id` so a bot's traces stay greppable across restarts:

```python
BayseClient(..., trace_config=TraceConfig(session_id="marketmaker-prod"))
```

## Error Handling

Every API error raises a subclass of `BayseError`, carrying `error_code`,
`status_code`, `response_headers`, and `timestamp`.

| Exception | Status | Notes |
|---|---|---|
| `InvalidSignatureError` | 401 | Signature mismatch — check the secret key. |
| `TimestampExpiredError` | 401 | Clock skew beyond the 5-minute window. |
| `UnauthorizedError` | 401/403 | Key missing or lacks permission. |
| `NotFoundError` | 404 | Resource does not exist. |
| `ValidationError` | 422 | Request rejected — read `.message`. |
| `RateLimitError` | 429 | Carries `.retry_after_seconds` when the header is present. |
| `InternalServerError` | 500 | Server-side. |
| `NetworkError` | — | Transport-level; never reached the API layer. |

**`NetworkError` tells you whether the request left your machine**, which is the
difference between safely re-sending a write and risking a duplicate:

```python
from bayse_markets.exceptions import NetworkError

try:
    await client.place_order(...)
except NetworkError as exc:
    if exc.request_sent is False:
        ...  # connect-phase failure: the server never saw it, safe to re-send
    else:
        ...  # None = unknown. The order may exist. Reconcile, do not re-send.
```

`False` means a connect-phase failure (`ConnectError`, `ConnectTimeout`,
`PoolTimeout`, `ProxyError`) — definitively never delivered. `None` means the
connection was live when it broke, so the outcome is genuinely unknown. The
original `httpx` exception is preserved on `.original_exception`.

## Known API Behaviours

Confirmed against the live API. These are venue behaviours, not SDK bugs — some
contradict Bayse's published docs.

- **`list_orders()` returns an empty page unless you pass `currency`.** A missing
  `currency` is not "all currencies" — it is a `200` with zero results and
  well-formed pagination. An account holding 60 NGN orders looks flat. The SDK
  logs a WARNING when this happens, but never use a bare call to conclude an
  account is empty. Values are case-sensitive.

- **`stp_mode` silently falls back to `SKIP` on any unrecognised value.** No error,
  no warning. The real set is `SKIP` (default), `CANCEL_OLDEST`, `CANCEL_NEWEST`,
  `CANCEL_BOTH`. A typo leaves a CLOB order with no self-trade protection while
  reading like working code.

- **`max_slippage` accepts 0–0.50**, not the documented 0.00–1.00, and is never
  echoed back in any response — so you cannot confirm afterwards which bound was
  applied. Whether the engine enforces it at fill time is unverified.

- **Minimum order amount is 100** in the quote currency.

- **Orders route on `outcome_id` alone.** `marketId` is accepted but not
  validated; the market is derived server-side from the outcome. Don't rely on it
  as a safety check.

- **Order statuses are lowercase**: `pending`, `open`, `partial_filled`, `filled`,
  `cancelled`, `rejected`, `expired`. The `status` filter accepts all of these
  *except* `pending`, so a status-by-status sweep silently misses pending orders.

- **`outcome` means different things on different routes.** The read routes send
  `outcomeId` + `outcomeLabel`; the place route sends `outcome` holding a UUID.
  The SDK normalises both to `.outcome_id`. Note that `PlacedOrder.type` holds the
  *side* — prefer `.side` and `.order_type`, which are consistent everywhere.

---

## Design Notes

**Typed everywhere.** Every endpoint returns `BayseResponse[T]` where `T` is a Pydantic model. No raw dictionaries, no guesswork about field names. Your editor's autocomplete works.

**Snake_case fields.** The API speaks `camelCase` (`createdAt`, `filledSize`). The SDK translates to `snake_case` (`created_at`, `filled_size`). You can still use the raw API field via `model.model_dump(by_alias=True)` if needed.

**Separate auth domains.** `BayseClient` uses HMAC-signed requests with API keys. `UserClient` uses email/password + session tokens. Two clients, two auth models — no mixing concerns.

**UserClient is a bootstrap tool.** Use it once to create API keys, then never touch it again. `BayseClient` is the permanent workhorse.

**One-time secret keys.** When creating or rotating API keys, the `secret_key` is only returned once. Save it immediately.

---

## License

MIT — see [LICENSE](LICENSE). This project is unaffiliated with Bayse; "Bayse Markets" refers to the third-party API it wraps.

---

Full API reference at [docs.bayse.markets](https://docs.bayse.markets).
