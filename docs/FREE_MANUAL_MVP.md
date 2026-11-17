# Free manual Portfolio Insider intake

## Product boundary

The free version accepts one self-reported spot asset or one existing linear
USDT futures position per check. No paid tier is enabled. CEX sync, API keys,
DEX wallet ingestion, account authentication and full transaction reconciliation
are deferred. The page has no LLM calls or per-request infrastructure cost.

Inputs remain in page memory; there is no automatic localStorage or server
submission of portfolio data. Export is an explicit local JSON download. No
credentials should be entered. Source/venue text is user-entered metadata, not
an authenticated connection. The form is not evidence of a complete portfolio.

## Implemented

- VI / EN / simplified Chinese: `site/manual.html?lang=vi|en|zh`.
- Intent, asset, venue, and intended horizon before scenario calculations.
- Cycle (month/week/day), swing (day/H4/H1), intraday (H4/H1/M15) request profiles.
- Profiles are proposed market-data requirements only: no live calls, independent
  market-agent runs or circuit checks are initiated by the manual page.
- Spot: current and post-purchase average cost, unrealized PnL, remaining cash,
  allocation and hypothetical price loss against selected limits.
- Futures: LONG/SHORT linear USDT PnL, single-position equity and hypothetical
  additional loss from current reference price. No liquidation/margin approval.
- Local JSON export labels SELF_REPORTED / NOT_RUN / NOT_REQUESTED.
- Invalid input clears earlier results. Mode changes invalidate prior conclusions.
- No automatic trading, portfolio sync or persistent customer database.

## Important accounting boundaries

Spot assumes no borrowing, no fees/slippage/tax and manually USD-normalized
amounts. It does not infer realized PnL or historical account performance.

Futures quantities are underlying units, not contract counts. Wallet balance
excludes unrealized PnL, which is then added once. The model assumes this is the
only position in the futures wallet. Funding, fees, open orders, collateral
haircuts and maintenance margin are excluded. It cannot establish whether the
position survives to the hypothetical price. Positive equity is not margin
safety. Inverse contracts and options are unsupported.

The initial free scope is intentionally small. Do not display invented server
quotas or subscription offers. Any future AI explanation budget and paid data
integration require real service limits and a separately designed offering.

## Validation

Six Node tests cover the OKB 400/200 USD example, retained unrealized loss,
invalid numbers and unsupported scope, review-versus-purchase intent,
long/short PnL direction, additional loss versus entry loss, and nonpositive
equity. The existing Python market-data and independent-agent tests are separate.
