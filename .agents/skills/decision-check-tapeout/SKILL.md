---
name: decision-check-tapeout
description: Design or review Decision Check fixed-point encodings, TapeOut gate equivalence, and X Layer read-only circuit verification.
---

Read [the three-logic contract](../../../docs/THREE_LOGIC.vi.md) and [P2 in the roadmap](../../../docs/ROADMAP.md). Use `decision_check/decision_logic.py` as the six-bit reference and the Portfolio Insider candidate checks as inputs to numeric rule design.

Specify bit order, sign, scale, units, rounding, bounds and rejection of overflow before designing a comparator. Compare all 64 Boolean combinations and numeric equality, adjacent values, extrema and invalid inputs with the reference. Use synthetic values for public vectors. Record cost and gate counts only for the measured target.

Before claiming verification, bind the read result to chain ID, circuit identity, encoding version, input and block hash. Keep onchain outcomes separate from the underlying snapshot authenticity and from the decision status. Review network and protocol upgrade assumptions before any proposed deployment.
