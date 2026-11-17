# Market data and report pipeline — 2026-11-18

## Implemented

- Binance Spot: `https://data-api.binance.vision/api/v3/time` and `/api/v3/klines`.
- Binance USD-M Futures: `https://fapi.binance.com/fapi/v1/time` and `/fapi/v1/klines`.
- Explicit market selection; no implicit switch from spot to futures or to another venue.
- No keys, wallet, account endpoint or order path. Symbols currently restricted to USDT pairs.
- One exchange server-time cutoff per snapshot, passed as `endTime` to every request.
- D1 120, H4 240, H1 300 and M15 300 closed native candles. Overfetch five before filtering.
- Reject invalid OHLCV, duplicates, missing bars, incorrect intervals, stale final bars and missing frames.
- Reference price is the last CLOSED M15 close, not a live ticker or a derivatives mark price.
- Full raw public snapshot, source, market, cutoff, SHA-256, pinned engine revision and settings in report.
- Wyckoff H4, SMC H1 and confluence computed by pinned upstream modules.
- Local SQLite storage keyed by full-report digest. Repeated identical reports do not duplicate rows.
- Python replay validates snapshot structure/hash and recomputes analysis without network calls.
- Browser importer validates supported metadata, candle structure and snapshot checksum. It does not recompute analysis or authenticate the producer.

## Source references

- Binance Spot public market-data-only endpoints:
  https://github.com/binance/binance-spot-api-docs/blob/master/faqs/market_data_only.md
- Binance USD-M kline documentation:
  https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data
- Analysis source, MIT:
  https://github.com/superfual/Wyckoff-smc-swing-agent/tree/ca6dce03685317e980d435d22539cc8d0bf45e15

## Validation and connectivity

The offline suite covers source/market routing, pinned cutoff, closed-candle
filtering, invalid/gapped/duplicate/stale data, deterministic analysis replay,
modified reports, unsupported versions and SQLite idempotence.

An actual Spot collection was attempted in the development executor. Its network
request did not complete because network approval was cancelled. This is NOT a
verified API success, NOT evidence of a Binance outage, and NOT a valid live report.
No synthetic output is labeled live. The downloadable example has kind
`SYNTHETIC_TEST` and is for UI/engine plumbing only, not trading performance.

Production outbound access, rate limits and error handling must be checked on the
chosen Python runtime before enabling a live report button. The hosted static
site currently supports report import, not a hosted Python analysis endpoint.

## Persistence and reproducibility

The default `decision-check.sqlite3` is local, single-owner storage of public
market reports. It is not a deployed multi-tenant account database. Reports can
also be exported as JSON and verified independently. This is mathematical
repeatability, not cryptographic proof of market-source authenticity. The report
hash does not sign or encrypt data. TapeOut status remains NOT_REQUESTED.

## Next source adapters

OKX (including an OKB instrument after explicit instrument validation) is planned.
No OKX, DEX, option chain, mark/index price, open interest or funding adapter is
implemented here. Never silently substitute a different venue or contract.
Private portfolio fills, balances, fees and collateral require a separate,
explicitly scoped read-only import and must not be written to public examples.

## Deployment direction

Use a Python service for this pinned engine, a controlled request queue/cache,
source freshness checks and persistent snapshots. Do not expose this CLI as an
unauthenticated unbounded public process. A service must add authentication,
quotas, request limits, monitoring and backup/restore. No paid service is enabled
by this change. A Cloudflare static site cannot execute these Python modules.

## Successful collection retry — 2026-11-18 (Vietnam time)

The development executor successfully collected BTCUSDT Spot directly from the
Binance public market-data API. Source cutoff: 2026-11-17T18:22:09.846Z
(2026-11-18 01:22:09.846 UTC+7). D1 120, H4 240, H1 300, M15 300
closed candles passed validation; independent local replay returned REPLAY_MATCH.
The public snapshot is `site/observed-market-report.json`. It contains public
market data only. This is a recorded observed snapshot, not a continuously
updated feed or a hosted analysis API. Earlier connectivity limitations above
remain historical context and must not be read as the result of this retry.

Source access from the executor does not establish that the production hosting
platform can fetch the same data or execute Python. That deployment is still pending.

A separate BTCUSDT USD-M Futures retry returned HTTP 451 from the configured
Futures endpoint in this executor. No Futures report was generated. Spot success
does not imply Futures availability; no alternate route or market was substituted.
