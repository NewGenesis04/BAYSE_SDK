# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/NewGenesis04/BAYSE_SDK/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/NewGenesis04/BAYSE_SDK/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/NewGenesis04/BAYSE_SDK/releases/tag/v0.1.0
