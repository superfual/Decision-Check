# Development roadmap

Milestones below are proposals, not completed integrations or date commitments.

## P0 — Agent-to-site bridge

- Pin an upstream Wyckoff–SMC agent commit.
- Define a report schema: symbol, market type, timeframes, source, candle cutoff, data validity, strategy configuration, evidence, uncertainty, action and agent revision.
- Export an actual agent-run report and import it into the site.
- Clearly label live reports, historical snapshots and synthetic examples.
- Keep UNKNOWN / DATA_UNAVAILABLE; do not convert missing evidence to TRUE.

Acceptance: valid reports render with provenance; malformed, unsupported and stale inputs do not produce a ready-to-buy conclusion. Imported files remain untrusted until validated. A hash alone does not authenticate the producer.

## P1 — Portfolio accounting and risk

- Define opening balances, fills, partial sells, fees and base/quote assets.
- Use decimal arithmetic and a documented weighted-average cost convention.
- Distinguish deposits/withdrawals from investment returns.
- Separate realized PnL, unrealized PnL and aggregate performance.
- Calculate post-purchase average cost, reserves and allocation.
- Add user-defined exit-price loss budgeting with explicit gap/slippage limitations.
- Never use drawdown alone as a reason to DCA.

Acceptance: reconcile known transaction examples, including partial exits, fees and transfers; reject invalid histories and label user-entered data self-reported. The selected accounting convention is not tax guidance.

## P2 — TapeOut feasibility and numeric circuit

- Inspect the target deployment's supported interfaces and upgrade assumptions.
- Specify units, integer widths, bounds, rounding and overflow handling.
- Start with one reserve or allocation comparison; measure gate count, calldata and execution cost.
- Verify REF availability before reusing components.
- Compare deployed outputs with a local deterministic reference, including boundary cases.
- Review the exact fee and request owner wallet authorization before any paid deployment.

Acceptance: publish circuit contract/ID, design, encoding and read block, with reproducible input/output cases. Failed verification must not produce a successful onchain badge.

## P3 — Independent decision verification

- Record data cutoff, snapshot identity, portfolio snapshot, rule version, agent revision/settings, circuit identity, input encoding, output and chain read block.
- Provide a separate verifier and scenario comparison.
- State which fields were recomputed, authenticated, hashed or merely supplied.
- Keep private portfolio histories off public-chain records by default.

Acceptance: the same pinned deterministic computation can be reproduced. Changes are detectable against a trusted reference; changing the rule creates a new version. A hash is neither encryption nor proof that computation occurred.

## P4 — Read-only data integration and operations

- Add a service or scheduled report pipeline for the Python agent.
- Validate market-source availability outside the ChatGPT connector.
- Add opt-in read-only ledger imports, user isolation and secret management.
- Define storage, retention/deletion, monitoring, backups and restore checks.
- Measure latency and concurrent usage before scaling infrastructure.

Automated execution, custody and token issuance are separate scopes. Containers and DeWEB are optional research directions, not prerequisites.


## Portfolio Insider: unified multi-exchange portfolio (future phase)

The current public Spot pilot uses one shared exchange and manual holdings. The proposed amount is user-entered; funding choices come only from the stablecoins entered in the portfolio, with available quantities.

A future production version should aggregate the investor's authorized read-only balances across supported exchanges, normalize asset identity and USD valuations, reconcile transfers to avoid double counting, and report portfolio health across all accounts: total NAV, cash/stablecoin share, concentration, average costs, unrealized PnL and risk-budget usage. Report source coverage, timestamps and incomplete accounts. Exchange connectors and permissions must be implemented and verified before claiming synchronization is available. No withdrawal, trading or order-execution permissions are needed for this analytical scope.
