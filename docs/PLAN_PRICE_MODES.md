# Spot plan prices and risk inputs

- MARKET uses a fresh public Spot quote from the selected venue and records its source/time; it is a reference, not a guaranteed execution price. A missing or stale quote cannot silently become a manual fill price.
- LIMIT uses a user-entered hypothetical fill. Current portfolio marks remain current marks; the fill is not represented as an executed order. Explicit entry_mode is passed to the Python brain.
- Holding periods: under one month; one to under six months; six months and longer. This is independent of the candle-analysis profile.
- Asset cost-based loss tolerance and whole-portfolio NAV-anchor drawdown are distinct. Never synchronize their percentages.
- When adding an existing asset at the same venue, reuse its asset-level threshold from intake so the user does not re-enter it.
- The adverse price is the user's personal worst-case scenario, not an agent forecast or an actual stop order.
