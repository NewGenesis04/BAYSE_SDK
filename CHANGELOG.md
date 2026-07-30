# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-07-30

### Added

- `client.buy()` — high-level helper that calls `place_order` with `side="BUY"`.
  Takes `event_id`, `market_id`, `outcome_id`, `amount` (cash spend), and forwards
  to `place_order` with `side="BUY"` and `currency="NGN"` by default.

- `client.sell()` — high-level helper that calls `place_order` with `side="SELL"`.
  Takes `outcome_id`, `shares` (share count to liquidate), and optionally
  `event_id`/`market_id`. If the latter are omitted, they are resolved
  automatically from the user's portfolio by matching `outcome_id`. Raises
  `ValueError` if no active position is found.

- Manual test suite at `manual_test/test_buy_sell.py` covering both `buy()` and
  `sell()` happy paths, error cases, and the auto-resolution fallback.

### Changed

- `place_order()` docstring now explicitly documents the asymmetric `amount`
  semantics: cash spend on BUY, share count on SELL. The opening line also
  suggests preferring `buy()` or `sell()` for clearer semantics.

## [0.2.1] - 2026-07-29

A code review after the 0.2.0 release surfaced one unsafe default and several
pieces of undocumented API behaviour. Nothing here changes a signature, but the
first entry under Changed **does** change runtime behaviour — read it before
upgrading if you write to the API.

### Changed

- **`RetryConfig.retry_unsafe_on_statuses` now defaults to `()` instead of
  `(429,)`. Non-idempotent requests are no longer retried on anything.**

  0.2.0 retried a `POST` on `429`, reasoning that the rate limiter rejects
  over-budget writes before they reach the matching engine. That reasoning came
  from a line in the API docs written about the *batch* routes, and applying it
  to single order placement was an inference about server infrastructure that a
  client cannot verify. With the default `max_retries=5`, being wrong costs six
  live order submissions on a route with no idempotency support.

  Live probing also found the documented rate limits unenforced — 200 reads at
  ~65/s and 200 writes at ~58/s against documented limits of 30/s and 20/s
  produced zero `429`s. So the old default bought an unmeasurable benefit for a
  real tail risk.

  Restore the previous behaviour explicitly if you know where your limiter sits:

  ```python
  RetryConfig(retry_unsafe_on_statuses=(429,))
  ```

- Documented that `PlacedOrder.type` holds the order **side** (`"BUY"`), not the
  order type. The place route puts the side in `type` and the type in
  `orderType`, inverting the read routes, so reading `.type` expecting
  `LIMIT`/`MARKET` silently yields a side. Prefer `.side` and `.order_type`,
  which mean the same thing on every route — the place response populates `side`
  too, so nothing is lost. Field mapping is unchanged; it was simply unmarked.

- `max_slippage` now documents that enforcement at fill time is **unverified**.
  Only submission-time validation has been observed, and this API has precedent
  for accepting a parameter and ignoring it (`stp_mode` silently falls back to
  `SKIP`). Treat it as defence in depth behind your own price checks, not as a
  guaranteed server-side guard.

- The `idempotency_key` parameter on the three batch methods now documents that
  the server genuinely **deduplicates** on it, rather than merely accepting it.
  Verified live: the same key with an identical body returns the *original* order
  id and creates one order, while two distinct keys with the same body create
  two. A batch of one is therefore the only safe write-retry path this API
  offers — `place_order` has no idempotency support at all.

### Added

- `Order.outcome_label` — the human-readable outcome name (e.g. `"Up"`) returned
  by the order-read routes. It was previously parsed and discarded. Outcome
  labels are arbitrary per-market strings rather than `YES`/`NO`, so this is the
  only way to render an outcome without a second lookup.

## [0.2.0] - 2026-07-29

Retries are now aware of HTTP method semantics, so a failed write is no longer
replayed on the same terms as a failed read. See [Migrating to 0.2.0](#migrating-to-020).

### Added

- `NetworkError.request_sent` distinguishes a request that never left the machine
  from one that may have been processed. `False` for connect-phase failures
  (`ConnectError`, `ConnectTimeout`, `PoolTimeout`, `ProxyError`) — the server
  definitively never saw it. `None` for read-phase failures, where the outcome is
  genuinely unknown. The originating `httpx` exception class is preserved on
  `original_exception` and named in the error message.

  ```python
  except NetworkError as exc:
      if exc.request_sent is False:
          ...  # safe to re-send
  ```

- `RetryConfig.retry_unsafe_on_statuses`, `RetryConfig.safe_methods`, and
  `RetryConfig.idempotent_methods`.
- `RetryStrategy.is_idempotent(method, idempotent=False)`.

### Changed

- **BREAKING: retries are method-aware.** Non-idempotent requests are held to a
  separate, narrower status set than safe and idempotent ones.

  | Request | Retried on |
  |---------|-----------|
  | `GET` / `HEAD` / `OPTIONS` | `429, 500, 502, 503, 504` |
  | `DELETE` / `PUT` | `429, 500, 502, 503, 504` |
  | `POST` | `429` only |
  | `POST` with an `Idempotency-Key` | `429, 500, 502, 503, 504` |

  Previously every request retried on the same set, so a `POST` that returned
  `502` was replayed — but a `502` can mean the upstream processed the request
  and only the response was lost, which risks a duplicate order. This also
  affects `UserClient`, where `rotate_api_key` returns its secret exactly once: a
  silent replay would rotate a second time and strand the first secret
  unrecoverably.

  `POST` still retries on `429` on the basis that rate-limited writes are
  rejected before reaching the matching engine. Set
  `RetryConfig(retry_unsafe_on_statuses=())` to disable retries on
  non-idempotent requests entirely.

- **BREAKING: `RetryStrategy.should_retry()` requires a keyword-only `method`
  argument** and accepts an optional `idempotent` flag. Custom retry strategies
  must be updated.

- **BREAKING: `Order.outcome` and `PlacedOrder.outcome` are renamed to
  `outcome_id`.** Both have always held an outcome UUID, not a `YES`/`NO` label —
  the read routes spell it `outcomeId` on the wire, the place route spells it
  `outcome`, and the old field name made the latter look like a label. No
  compatibility shim: the attribute is gone rather than deprecated.

  Serialisation with `model_dump(by_alias=True)` is **unchanged** — it still emits
  `outcomeId`, matching the API. Only unaliased `model_dump()` changes, from
  `outcome` to `outcome_id`.

- Retries of non-idempotent requests log at `WARNING` with the trace ID and
  attempt number, rather than `DEBUG`. A replayed write is the one event an
  operator needs in their scrollback without having enabled debug logging in
  advance.

- `batch_place_orders()` and `batch_amend_orders()` mark the request idempotent
  when an `idempotency_key` is supplied, re-enabling `5xx` retries for them.

### Fixed

- `list_orders()` warns when it returns an empty page and no `currency` filter
  was supplied. The API does not treat a missing `currency` as "all currencies" —
  it returns an empty page with a `200` and well-formed pagination, so an account
  holding orders in one currency appears empty when queried without one. Code
  that reconciles state from this method would otherwise conclude there was
  nothing to reconcile. Behaviour is unchanged; the warning and documentation are
  new.

- Corrected the documented self-trade prevention modes. The valid set is `SKIP`
  (default), `CANCEL_OLDEST`, `CANCEL_NEWEST`, `CANCEL_BOTH`. Previous docs
  listed `DECREMENT_AND_CANCEL`, which does not exist, and omitted two that do.
  Unrecognised values are accepted and silently fall back to `SKIP`, so callers
  following the old documentation were placing CLOB orders with no self-trade
  protection while believing otherwise.

- Corrected the documented `max_slippage` range to 0–0.50. Values outside it are
  rejected with `400`. The value is validated on submission but is not echoed
  back in any response, so an order cannot be inspected afterwards to confirm
  which bound was applied.

### Migrating to 0.2.0

Most callers need no changes. Review your code if any of the following apply:

1. **You relied on `POST` requests retrying after a `5xx`.** They no longer do.
   For batch order routes, pass `idempotency_key` to restore retries safely. For
   single order placement, the API does not honour idempotency keys, so a `5xx`
   now surfaces to you and the order state must be treated as unresolved —
   reconcile via `list_orders()` before re-sending.

2. **You implemented a custom `RetryStrategy`.** `should_retry()` now takes a
   keyword-only `method` argument.

3. **You read `Order.outcome` or `PlacedOrder.outcome`.** Rename to `outcome_id`.
   The attribute is gone, so this fails loudly with `AttributeError` rather than
   silently. If you serialise with a bare `model_dump()`, the key changes too;
   `model_dump(by_alias=True)` is unaffected.

4. **You call `list_orders()` without `currency`.** Pass it explicitly, once per
   currency you trade. A bare call cannot be used to conclude an account is flat.

## [0.1.0] - 2026-07-19

- Initial release.

[Unreleased]: https://github.com/NewGenesis04/BAYSE_SDK/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/NewGenesis04/BAYSE_SDK/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/NewGenesis04/BAYSE_SDK/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/NewGenesis04/BAYSE_SDK/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/NewGenesis04/BAYSE_SDK/releases/tag/v0.1.0
