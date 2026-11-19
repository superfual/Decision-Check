# Portfolio Insider — Spot-only pilot

The first public experiment covers coin/token and stablecoin holdings and Spot investment plans.

- NAV updates from quantity × current price across listed Spot assets.
- Unrealized PnL uses quantity × (current price − average cost).
- Preserve the two risk limits: the original decision amount and the fixed cycle NAV anchor.
- A proposed asset need not already be held.
- Portfolio Insider comes first; Wyckoff and SMC independently analyze the same selected Spot market scope.
- No order execution or account connection.

Futures and options are deferred. Their existing research code and regression tests are retained, but the public intake and handoff reject derivative portfolios and plans. A later release needs explicit contract identity, fees/funding, margin and liquidation rules, and options valuation/expiry risk before enabling those products.
