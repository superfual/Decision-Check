# Spot plan prices and risk inputs

- MARKET uses a fresh public Spot quote from the selected venue and records its source/time; it is a reference, not a guaranteed execution price. A missing or stale quote cannot silently become a manual fill price.
- LIMIT uses a user-entered hypothetical fill. Current portfolio marks remain current marks; the fill is not represented as an executed order. Explicit entry_mode is passed to the Python brain.
- Holding periods: under one month; one to under six months; six months and longer. This is independent of the candle-analysis profile.
- Asset cost-based loss tolerance and whole-portfolio NAV-anchor drawdown are distinct. Never synchronize their percentages.
- Ask once in Step 01 for the investor’s shared cost-based cycle tolerance; apply it to existing and newly proposed Spot assets without asking again.
- The adverse price is the user's personal worst-case scenario, not an agent forecast or an actual stop order.


## Shared investor cycle tolerance

The public Spot intake asks once for the investor's cost-based cycle loss tolerance. That percentage is applied consistently to each existing Spot holding and any proposed asset, regardless of ticker. Individual cost bases still produce different reference prices. The proposed-purchase loss tolerance is shown beside the user-entered purchase amount. The whole-portfolio NAV-anchor limit remains mathematically separate; it must not be silently equated to an asset-price decline.


## Adjustable cash-safety percentage

The Spot intake asks for a minimum cash/stablecoin share of total current portfolio NAV, default 20%, editable from 0 to 100%. The requested purchase and the bounded alternative both report remaining cash and cash percentage. The sizing engine includes this constraint alongside the selected funding bucket and existing risk constraints. Buying Spot converts cash into an asset; with no fee buffer NAV is unchanged, so the cash cap is max(0, cash − selected_percentage × NAV). A nonzero loss buffer reduces both cash and NAV and is included in the exact inequality. If current cash is already below target, the additional-purchase cap is zero and the gate remains unmet. This is a point-in-time analytical constraint, not a promise about future market prices.
