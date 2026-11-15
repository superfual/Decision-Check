# Architecture and verification boundaries

| Layer | Responsibility | What it does not establish |
| --- | --- | --- |
| Market-data adapter | Source, timestamp and closed-candle validation | Infallibility of an external source |
| Python agent | Wyckoff/SMC evidence, thesis and uncertainty | Guaranteed future price behavior |
| Ledger calculator | Cost basis, PnL and proposed changes | Completeness of supplied account history |
| Rule adapter | Version rules and encode bounded numeric/Boolean inputs | Correctness of offchain interpretation by itself |
| TapeOut evaluator (planned) | Evaluate specified circuit inputs | Authenticity of those inputs by itself |
| UI and verifier | Explain constraints and provenance | That local simulation is an onchain execution |

## Current implementation

Three-language static HTML/CSS/JavaScript. Manual signals and sample numbers, local calculation and JSON export. No backend, agent connection, exchange account connection or deployed circuit for Decision Check.

## Sample portfolio rule

For spot holdings without debt:

- V = quantity held × assumed current price
- N = V + cash + other asset value
- B = proposed purchase value

Check B ≤ cash, cash − B ≥ minimum reserve, and (V + B) / N ≤ allocation limit.

A proposed numeric circuit can avoid allocation division by comparing:

100 × (V + B) ≤ allocationLimitPercent × N

This is a design direction, not deployed circuit code. Fixed-point units, bounds, rounding and overflow must be specified first.

## Boolean composition versus full analysis

WyckoffPass AND SMCPass AND PortfolioPass checks the combination of supplied flags. It does not prove how Wyckoff/SMC features were extracted. Deeper verification requires explicitly encoding specific numeric or structural rules. UNKNOWN needs a validity signal and must not silently become a pass.

## Reproducibility

Pin data cutoff, snapshot, rule version, code revision and settings. Arbitrary LLM interpretations are not guaranteed to reproduce. Independent verification should cover explicitly specified deterministic computations.

## State and execution

Reading/evaluating a circuit is different from updating onchain state. A LATCH alone does not schedule work, authorize changes or send transactions. A policy output does not automatically block an exchange order; actual enforcement requires a separate execution design.

## Privacy

Do not publish private account ledgers or credentials. Canonical records and hashes need a threat model; hashing does not encrypt low-entropy data or authenticate a producer.
