# Three-logic consistency

Portfolio Insider and market aggregation fetch the same browser Python core at `portfolio-brain/brain.py`. Version `portfolio-insider.brain.v1.1` includes cash-safety gates. Run `python scripts/sync-browser-runtime.py` before packaging and the consistency tests to detect stale generated copies.

Aggregation compares both portfolio as-of and market collection cutoff with its aggregation clock. Each must be nonfuture and no more than one hour old. Market collection may follow portfolio entry. Closed-candle validation remains separate and unchanged. Live calls use the current UTC clock; offline tests/replay pass an explicit recorded evaluation time, labeled `RECORDED_REPLAY` in the result. Never present an old replay as fresh market analysis.

Aggregation recomputes from original inputs and checks the prior report engine version. A mismatch requires returning to Portfolio Insider. Every Spot report must include decision, cycle, available-funding, anchor and cash-safety gates; missing checks make the combined result UNKNOWN. Market disagreement remains RULES_NOT_MET when inputs are valid. No TapeOut deployment or chain verification is implied.

Validation: `python -m unittest discover -s tests -p 'test_three_logic_consistency.py'`. Covers sequential collection, stale/future inputs, identical standalone/combined reports, cash-safety failure, version mismatch, missing checks and generated source parity.
