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


## Current portfolio risk summary

The public form reads the cycle loss percentage from the investor's single intake field and displays it read-only below. The portfolio reference value is calculated from the current listed holdings, and the reference time equals the selected analysis time. This is a current-snapshot loss budget, not historical drawdown tracking. No separate default 20% is applied to cycle loss; the adjustable cash-safety ratio remains independent. The UI does not ask users to reconcile historical flows for a newly established point-in-time reference.


## Whole-portfolio loss boundary
- The shared cycle percentage is a loss budget against current total NAV, not a decline from each asset's average cost.
- For a holding with quantity q, current NAV N and other holdings worth O, its conditional boundary price is (N × (1 − loss_pct/100) − O) / q. Stablecoins and all other assets are held at their current value. Average cost affects unrealized PnL, not this boundary.
- If O exceeds the NAV floor, no nonnegative price for this asset alone can breach the limit; display that fact instead of a negative stop price. Incomplete balances suppress the boundary.
- The analysis tests the planned asset at the user's adverse price; other holdings and stablecoins remain unchanged. This assumption is displayed and exported. It is not a forecast or a combined market-crash simulation.
- Removed the BTC + USDT example button and its data-populating handler.
