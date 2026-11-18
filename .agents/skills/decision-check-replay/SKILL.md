---
name: decision-check-replay
description: Implement or review Decision Check snapshot validation, versioned report contracts, deterministic replay, and CLI/browser parity.
---

Read [the three-logic contract](../../../docs/THREE_LOGIC.vi.md) and [the Hybrid architecture](../../../docs/HYBRID_DEWEB.vi.md).

Trace legacy verification in `decision_check/reports.py` and three-branch computation in `decision_check/decision_logic.py`. Keep legacy reports replayable. For a new envelope, identify the exact canonical bytes, hash algorithm, ruleset revision, configuration and cutoff needed by the verifier. Recompute from original inputs and compare with the report, treating self-reported inputs and externally authenticated inputs according to their provenance.

Use synthetic fixtures under `examples/market-brains/` and `examples/portfolio-insider/`. Cover the requested amount, scope mismatch, stale cutoff, unknown evidence, a modified report and unsupported versions. Check `site/market-runtime/decision_check/` and `site/portfolio-brain/brain.py` when a shared module changes. Record which paths replayed and which fields remained supplied.
