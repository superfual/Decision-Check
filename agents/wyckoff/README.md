# Wyckoff Agent v2

Independent deterministic context/range/event analysis. Shares a validated snapshot
with SMC; never consumes SMC results. Uses the creator's pinned MIT upstream
`ca6dce03685317e980d435d22539cc8d0bf45e15` unchanged at the primitive layer.
The new adapter applies timeframe-neutral series operations explicitly; it does
not call a 4H-only wrapper while claiming to analyze weekly candles.

| Profile | Context | Wyckoff series | SMC (separate agent) |
| --- | --- | --- | --- |
| CYCLE | Monthly (60 closed) | Weekly (120) | Daily (300) |
| SWING | Daily (120) | H4 (240) | H1 (300) |
| INTRADAY | H4 (120) | H1 (300) | M15 (300) |

The 30-bar range detector uses quantile boundaries, containment, touch count and
limited displacement. Ordered bullish evidence is SC → AR → ST → SPRING → SOS;
bearish is BC → AR_DOWN → UT_TEST → UTAD → SOW. See vendor/wyckoff.py for
numeric volume/spread/reclaim thresholds. TEST/LPS or UTAD_TEST/LPSY are displayed
as supporting evidence but are not mandatory gates in this v2 ruleset.

A direction passes only if all checks pass: stable range; ordered sequence;
confirmation no older than ten analysis bars; no subsequent close through the
sweep extreme; higher-timeframe close/SMA20/SMA50 context not opposite; inferred Wyckoff bias agrees. Neutral
higher-timeframe context is allowed, not equivalent to positive confirmation.
No range means valid analysis with rules unmet, not missing data. Invalid input
means UNKNOWN. Existing scores are heuristic scores, **not probabilities**.

This is a deliberately narrow accumulation/distribution setup checker. Trending
markets can have no range; that is not proof that no opportunity exists. OHLCV
cannot establish actual whale identities, intent, or guaranteed accumulation.

API: `WyckoffBrain().run(profile_snapshot)` in `decision_check.market_brains`.
Reports bind scope, timeframe, cutoff, snapshot hash and rule version, with every
check and its evidence. [Three-logic contract](../../docs/THREE_LOGIC.vi.md).
No circuit has been deployed; no trades are executed.
