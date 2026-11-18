# SMC Agent v2

Independent deterministic structure/liquidity analysis from the same profile
snapshot as Wyckoff, without reading Wyckoff's conclusion. Pinned MIT upstream
algorithms detect confirmed swing highs/lows (2 left/2 right bars), close-confirmed
BOS/CHoCH, equal-high/low pools, sweeps, displacement FVGs and order blocks.

The v2 pass rule is deliberately stricter than a directional bias:

1. A same-direction liquidity sweep precedes a close-confirmed BOS/CHoCH.
2. A displacement order block is linked to that exact break and is FRESH or TOUCHED.
3. The break is within the latest ten analysis bars.
4. No subsequent close has broken through the sweep extreme.
5. The latest structure direction still agrees.
6. Higher-timeframe context is not opposite (neutral is permitted).

FVGs are reported with their mitigation state but a lone FVG is **not** sufficient
to pass this v2 setup. Mitigated/invalidated order blocks do not qualify. There is
no promise that a detected zone will hold or that a stop will fill at its level.
Swing confirmation times are retained. Reports recompute the current snapshot;
they are not a proof of historical prefix-invariance or an audited backtest.

CYCLE uses daily SMC and monthly context; SWING uses H1 and daily context;
INTRADAY uses M15 and H4 context. See [Wyckoff profile counts](../wyckoff/README.md).
Monthly candles follow calendar boundaries and weekly candles Monday UTC;
missing history is UNKNOWN, never substituted with smaller frames or Spot.

API: `SMCBrain().run(profile_snapshot)` in `decision_check.market_brains`.
[Three-logic contract](../../docs/THREE_LOGIC.vi.md). No account connection,
order execution or deployed TapeOut circuit.
