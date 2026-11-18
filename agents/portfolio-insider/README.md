# Portfolio Insider Agent

A deterministic, offline analytical brain for Decision Check. It evaluates a
proposed spot purchase or same-direction linear futures addition against two
separate risk budgets. It never submits orders or connects to private accounts.

```sh
python3 -m decision_check.portfolio_insider examples/portfolio-insider/bnb-dca-negative.input.json --out /tmp/portfolio-report.json
```

Python API: `PortfolioInsiderAgent().run(input_dict)` from
`decision_check.portfolio_insider`. Standard library only. Use decimal strings for
money, prices, quantities and percentages; binary floats are rejected. Invalid,
incomplete and unsupported inputs return `NEEDS_DATA_OR_UNSUPPORTED`, never a pass.
CLI exits 2 on such reports. Outputs contain an input SHA-256 for deterministic
replay; a hash is not source authentication or proof of account completeness.

See [the complete brain design](BRAIN.vi.md), the synthetic input/report pairs in
`examples/portfolio-insider`, and `tests/test_portfolio_insider.py`.

## Input contract

- `schema`: `portfolio-insider.input.v1`; `as_of`: timezone-aware snapshot time;
  `reporting_currency`: explicit; `data_source`: `SELF_REPORTED`.
- `portfolio.cash`: disjoint buckets with id, asset, amount, available_amount,
  and fx_rate. USD/stablecoins need explicit conversion rates; parity is not assumed.
- `portfolio.spot`: id, asset, venue, quantity, current price, remaining cost_basis
  (nullable). Prices/cost are in the reporting currency. Cost is not lifetime deposits.
- `portfolio.futures_accounts`: id, settlement_asset, wallet_balance,
  available_margin (nullable), fx_rate. Do not duplicate this wallet in cash.
- `portfolio.futures`: id, account_id, asset, venue, LINEAR contract_type,
  LONG/SHORT direction, quantity, entry_price, mark_price. Prices are in settlement
  currency. Wallet plus unrealized PnL contributes to NAV, not position notional.
- `decision`: product SPOT/LINEAR_FUTURES; intent BUY_SPOT/ADD_SPOT or
  OPEN_FUTURES/ADD_FUTURES; asset, symbol, venue, position_id (null for new),
  funding_id, profile CYCLE/SWING/INTRADAY, holding_horizon, proposed_amount,
  loss_tolerance_pct, entry_price, stop_or_scenario_price, cycle_price.
  Futures also require direction and leverage. `proposed_amount` is reporting-
  currency notional, never margin. Optional allocated_loss_budget lowers the frozen
  budget; minimum_available_cash and loss_buffer_pct add constraints.
- `cycle`: anchor_id, anchor_as_of, anchor_nav, max_loss_pct,
  external_flows_reconciled=true and explicit scenario prices for **every** existing
  spot/futures position id. No missing asset is silently held unchanged.
- Optional `market_evidence`: plan scope (symbol/venue/market), profile, cutoff_ms,
  max_age_ms, snapshot_sha256 and separate wyckoff/smc reports (same hash,
  ANALYZED status, evidence symbol/bias/errors). Missing/conflicting evidence stays
  unknown/conflicting; supplied evidence is explicitly unauthenticated.

## Boundaries

This is snapshot analysis, not full transaction-ledger accounting. Realized PnL,
fee/funding reconciliation, options, inverse contracts, cross-margin liquidation,
correlations and calibrated probabilities are not implemented. Unsupported
products must be mapped to an explicit unsupported response, not treated as spot.
A scenario buffer is not a booked fee. SL prices are hypothetical, not placed or
guaranteed. Futures reports always leave margin/liquidation safety unverified.

Manual entry is the free first path. CSV adapters and private CEX/DEX sync are
future work with separate privacy/security requirements. No credentials belong
in input files or GitHub. The hosted manual MVP uses its existing calculator;
this Python brain has not yet been integrated into the site or hosted API.

TapeOut integration is a proposed next layer: encode precise numeric comparisons,
retain inputs/rule version and independently replay. No Decision Check circuit
is deployed or called by this agent. Wyckoff/SMC remain independent existing
runners; requested timeframe profiles do not upgrade their current H4/H1 logic.
