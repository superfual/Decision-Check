# Decision Check

**Market opportunity meets portfolio discipline.**

A concept-stage tool combining Wyckoff–SMC market evidence, portfolio accounting and proposed verifiable TapeOut rules on X Layer.

[English demo](https://fual-decision-check.phamphuanloc.chatgpt.site/en.html) · [Tiếng Việt](https://fual-decision-check.phamphuanloc.chatgpt.site/vi.html) · [简体中文](https://fual-decision-check.phamphuanloc.chatgpt.site/zh.html)

## Why build this?

Retail investors need to inspect the evidence behind signals, reconcile their cost basis and PnL, and determine whether buying more fits their own risk constraints. An interesting market opportunity can still be unsuitable for the portfolio.

## Current status

| Component | Status |
| --- | --- |
| EN / VI / simplified Chinese site | Implemented static prototype |
| Manual sample inputs and average cost | Implemented locally |
| Unrealized PnL for one sample position | Implemented under stated assumptions |
| Proposed purchase reserve and allocation checks | JavaScript simulation |
| JSON export | Local illustrative record, not onchain proof |
| Wyckoff–SMC engine | Pinned deterministic modules incorporated; market-evidence report pipeline implemented |
| Binance Spot / USD-M data | Direct public collectors implemented; production connectivity not verified |
| Snapshot storage | Local single-owner SQLite, idempotent report storage |
| Agent report page | EN / VI / ZH import, snapshot checksum and provenance; synthetic test example clearly labeled |
| Deterministic replay | Python verifier recomputes analysis from saved candles |
| Full ledger / realized PnL / modeled loss budget | Planned |
| Decision Check TapeOut circuits | Proposed; not deployed |
| Account connections and automated orders | Not implemented |

The Wyckoff and SMC selectors are **manual examples**, not actual outputs from the agent. The site needs no API keys or wallet and sends no portfolio input to a server.

## Existing analysis foundation

The creator's [Wyckoff–SMC Swing Agent](https://github.com/superfual/Wyckoff-smc-swing-agent) is the intended analysis foundation. Its orchestrator exposes structured Wyckoff, SMC, confluence, thesis and risk results, reasons and errors. This repository now incorporates four unmodified deterministic analysis modules from upstream revision `ca6dce03685317e980d435d22539cc8d0bf45e15`. The pipeline calls Wyckoff, SMC and confluence directly; it does not import the execution or account modules. See `decision_check/vendor/UPSTREAM.md` and its MIT license.

Live data access must be validated on the target host. The static site imports reports; it does not run Python or call a hosted analysis API. The original sample selectors remain manual and separate from imported market evidence.

## Request-scoped workflow

1. User selects a decision intent (spot purchase/review or futures open/review).
2. Portfolio Insider proposes the exact instrument, venue, product and data requirements from the selected portfolio or explicit user request.
3. The source router fetches one dataset; validation and snapshot persistence must succeed before analysis starts.
4. **Wyckoff Agent and SMC Agent run independently on the same snapshot.** Neither consumes the other's conclusion or fetches a separate feed.
5. Portfolio findings and the two evidence reports are combined only downstream; proposed TapeOut circuits check explicitly encoded quantitative conditions.
6. An explanation and alternative scenarios are presented without sending orders.

`decision_check/intake.py` implements the deterministic intake contract, source
routing boundary and data gate; `decision_check/agents.py` defines independent
analysis runners. Portfolio Insider now has an offline Decimal-based analytical
brain; account adapters and TapeOut circuits remain unimplemented. These runners are not deployed circuits
or separate LLM services. Their common snapshot hash binds the input, not its
authenticity. See [the intake architecture](docs/INDEPENDENT_AGENTS.md).

The legacy v1 combined report remains available for historical replay. It is not
the new independent-agent report or evidence of a deployed multi-agent service.

Example: Wyckoff and SMC meet the selected conditions, but a proposed purchase raises allocation to 60% against a 40% limit. The result is **conditions not met**, with the failing constraint visible. These are illustrative figures.

Passing rules does not guarantee profitability. A circuit cannot by itself authenticate market interpretations or establish complete account history.

## Documentation

- [Development roadmap](docs/ROADMAP.md)
- [Architecture and verification](docs/ARCHITECTURE.md)
- [Tiếng Việt](docs/OVERVIEW.vi.md)
- [简体中文](docs/OVERVIEW.zh.md)

## Run the prototype locally

No build step or package installation:

```sh
python3 -m http.server 8080 --directory site
```

Open http://localhost:8080/en.html, vi.html or zh.html.

The calculator assumes spot holdings, no debt, no fees or slippage, and no sells. Its unrealized PnL is not full account reconciliation. See the roadmap for the intended accounting upgrade.

## Collaboration

Contributions in portfolio accounting, deterministic strategy rules, TapeOut circuit design, UX and testing are welcome. Please open an issue describing the problem and proposed scope before substantial implementation.

This is an independent concept prototype, not an audited trading system or an official TapeOut/X Layer product. It does not claim to be the first or only such product. Automatic execution is outside the current scope.

## Market evidence pipeline (Python 3.11+, standard library only)

```sh
python3 -m decision_check collect BTCUSDT --market SPOT --out report.json
python3 -m decision_check collect BTCUSDT --market USD_M_FUTURES --out futures-report.json
python3 -m decision_check verify report.json
python3 -m unittest discover -s tests -v
```

Open `site/report.html?lang=en` (or `vi` / `zh`) through a local web server and import the report.
The complete public candle snapshot is included. SQLite stores reports locally; do not commit the database.
Browser checksum validation is not independent analysis replay or source authentication.
The Python verifier recomputes the pinned deterministic analysis. An attacker able to replace
both the snapshot and checksum can generate a new internally consistent record; retain a trusted reference.

See [Data sources and operations](docs/DATA_SOURCES.md) for boundaries and connectivity results.

## Free manual Portfolio Insider check

Open `site/manual.html?lang=vi` (also `en` / `zh`). The free scope is one spot
asset or one existing linear USDT futures position per check, with an explicit
intent and holding horizon. Inputs stay in page memory; JSON export is local.
No account synchronization, API credentials, LLM request or trade is involved.

The page calculates user-supplied scenarios and proposes a market-data profile.
It does **not** fetch the selected market data, run the independent agents or
verify TapeOut circuits. See [free MVP scope](docs/FREE_MANUAL_MVP.md).

```sh
node --test tests/manual-core.test.mjs
```

## Portfolio Insider analytical brain

[Brain specification (Vietnamese)](agents/portfolio-insider/BRAIN.vi.md) ·
[Agent usage and scope](agents/portfolio-insider/README.md)

```sh
python3 -m decision_check.portfolio_insider examples/portfolio-insider/bnb-dca-negative.input.json --out /tmp/portfolio-report.json
python3 -m unittest discover -s tests
```

The brain separates the loss budget of one proposed decision from whole-portfolio
cycle risk against a fixed NAV anchor. It reports DCA cost/PnL, cash ratios,
scenario bounds and linear futures notional sizing. Examples are synthetic.
It is not wired into the hosted UI, exchange accounts, or deployed TapeOut circuits.
