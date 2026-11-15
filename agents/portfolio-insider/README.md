# Portfolio Insider Agent

**Status: specification / incubation. No agent runtime or account adapter implemented.**

Portfolio Insider Agent is the portfolio-analysis component proposed for Decision Check. It will be developed thoroughly in a separate repository later; this branch gives it a defined identity and scope now.

## Mission

When a user explicitly requests analysis and supplies or connects read-only data, explain what their current holdings and positions reveal about exposure, cost basis, PnL and accepted risk.

This is not limited to long-term coin holdings. It includes Spot, Futures and Options. It does not place, amend, cancel or close orders, change leverage or margin, move assets, or request trading/withdrawal permissions.

## Three perspectives in Decision Check

| Component | Question |
| --- | --- |
| Wyckoff–SMC agent | What market context and structural evidence exist? |
| Portfolio Insider Agent | What do the user's existing positions imply about exposure and risk? |
| TapeOut rules, proposed | Do explicitly encoded quantitative constraints pass on the supplied inputs? |

The existing strategy repo is the analysis foundation, not proof that Portfolio Insider or all derivatives strategies already exist.

## Product scope

| Product | Intended analysis |
| --- | --- |
| Spot | Quantity, average cost, realized/unrealized PnL, cash, concentration and correlations |
| Futures | Direction, notional, contract specification, leverage, isolated/cross margin, funding and liquidation proximity when valid data is available |
| Options | Long/short call/put, strike, expiry, premium, contract multiplier, Greeks and scenario PnL |
| Combined portfolio | Economic exposure across products, hedges, concentration, scenario loss and liquidity needs |

Do not apply spot cost-basis arithmetic to every derivative. Linear and inverse contracts differ. Options require appropriate pricing assumptions, volatility inputs and expiry handling. Venue-specific margin rules matter. Greeks and stress results are model estimates, not guarantees.

## Example insights, not current outputs

- BTC Spot + BTC long Futures + BTC long Call may concentrate exposure to the same upward move despite different product labels.
- A BTC short may hedge Spot; judge the combined exposure rather than assuming the short is speculation.
- Lowering average cost can increase capital at risk beyond the user's limit.
- An option position can change with time and implied volatility even when the underlying barely moves.
- A position-level liquidation distance is not the same as a portfolio-level margin safety guarantee.

Every insight needs evidence, scope, timestamps and assumptions. Behavioral conclusions require adequate trade history; a balance snapshot cannot prove repeated chasing or averaging down.

## Proposed architecture

1. Explicit user request and read-only data scope.
2. Venue adapters or manual imports with provenance and coverage.
3. Product-aware normalization and deterministic accounting/risk tools.
4. Agent interpretation of those computed results.
5. Evidence-linked report, optional scenario comparison and proposed TapeOut policy checks.

A wallet connection alone does not reveal exchange accounts or all historical positions. Snapshot analysis must disclose missing fills, fees, funding, transfers or collateral data.

## Output contract to design

- Report ID, schema version, account scope, as-of time and data sources.
- Instrument type, venue, quote/base/settlement assets and contract multiplier.
- Observed positions and balances separated from derived metrics.
- Realized/unrealized PnL with accounting method, fee and funding treatment.
- Exposure, margin and scenarios with assumptions and model version.
- Findings: claim, supporting metrics, severity, uncertainty and missing data.
- User-defined risk thresholds; no assumed universal risk tolerance.
- Agent revision and calculation-rule version.
- TapeOut status: not requested, local only, verified or unavailable; never invent circuit IDs.
- Suggested review questions or alternatives, not execution instructions sent to a venue.

No private portfolio examples are included in this branch.

## TapeOut boundary

Start with bounded, specified numeric comparisons such as an exposure or modeled-loss limit, after feasibility testing. A circuit checks encoded rules over supplied inputs. It does not authenticate account history, prove qualitative agent interpretations or predict returns. Hashing a report does not prove it was computed correctly or conceal its contents.

## Acceptance before integration

- Decimal arithmetic and product-specific reconciliation fixtures.
- Fees, funding, partial exits and transfers handled explicitly.
- Combined hedge versus concentration examples.
- Freshness, missing-data and invalid instrument handling.
- Adapters have no trade/transfer method or permission requirement.
- Reports distinguish observed facts, deterministic calculations and interpretation.
- Private account data stays outside public GitHub and public chain records.
- No successful verification indicator on failed or absent circuit checks.

## Separate repository later

Create a dedicated repo only when the owner requests it. Move this specification with attribution/history references, select a license, define ownership and versioned report interfaces, then develop adapters, calculators, tests and the agent runtime there. Decision Check should consume the stable report interface rather than duplicate the agent.

Until then, this folder is the canonical incubation specification on this branch. It is documentation, not a deployed feature.
