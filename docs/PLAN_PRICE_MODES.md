# Spot plan prices and risk inputs

- MARKET uses a fresh public Spot quote from the selected venue and records its source/time; it is a reference, not a guaranteed execution price. A missing or stale quote cannot silently become a manual fill price.
- LIMIT uses a user-entered hypothetical fill. Current portfolio marks remain current marks; the fill is not represented as an executed order. Explicit entry_mode is passed to the Python brain.
- Holding periods: under one month; one to under six months; six months and longer. This is independent of the candle-analysis profile.
- Asset cost-based loss tolerance and whole-portfolio NAV-anchor drawdown are distinct. Never synchronize their percentages.
- Ask once in Step 01 for the investor’s shared cost-based cycle tolerance; apply it to existing and newly proposed Spot assets without asking again.
- The adverse price is the user's personal worst-case scenario, not an agent forecast or an actual stop order.


## Shared investor cycle tolerance

The public Spot intake asks once for the investor's cost-based cycle loss tolerance. That percentage is applied consistently to each existing Spot holding and any proposed asset, regardless of ticker. Individual cost bases still produce different reference prices. The proposed-purchase loss tolerance is shown beside the user-entered purchase amount. The whole-portfolio NAV-anchor limit remains mathematically separate; it must not be silently equated to an asset-price decline.
