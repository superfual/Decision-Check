"""Portfolio Insider intake contract, explicit source plan, then analysis fan-out.

This is a deterministic planning boundary; the Portfolio Insider interpretation
agent and authenticated portfolio adapters are not implemented here.
"""
from dataclasses import asdict, dataclass
import json
import re
import sqlite3
from .market import DataError, SOURCES, canonical, collect, digest, validate_snapshot
from .agents import WyckoffAgent, SMCAgent

INTENTS = {
    'BUY_SPOT': 'SPOT', 'REVIEW_SPOT': 'SPOT',
    'OPEN_FUTURES': 'USD_M_FUTURES', 'REVIEW_FUTURES': 'USD_M_FUTURES',
}


@dataclass(frozen=True)
class MarketDataPlan:
    venue: str
    market: str
    symbol: str
    intent: str
    scope_reason: str
    proposed_by: str = 'PORTFOLIO_INSIDER_INTAKE'


def propose_source(*, venue, market, symbol, intent, holding_symbols=(), requested_symbols=()):
    """Caller supplies explicit instrument scope; never discover or scan all markets."""
    if intent not in INTENTS or market != INTENTS[intent]:
        raise DataError('INTENT_MARKET_MISMATCH_OR_UNSUPPORTED')
    if venue != 'BINANCE' or market not in SOURCES:
        raise DataError('SOURCE_ADAPTER_NOT_IMPLEMENTED')
    if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9]{2,24}USDT', symbol):
        raise DataError('INVALID_SYMBOL')
    if symbol in requested_symbols:
        reason = 'EXPLICIT_USER_REQUEST'
    elif symbol in holding_symbols:
        reason = 'SELECTED_PORTFOLIO_INSTRUMENT'
    else:
        raise DataError('ASSET_OUTSIDE_AUTHORIZED_SCOPE')
    return MarketDataPlan(venue, market, symbol, intent, reason)


def _check_binding(plan, snapshot):
    validate_snapshot(snapshot)
    if (snapshot['venue'], snapshot['market'], snapshot['symbol']) != (plan.venue, plan.market, plan.symbol):
        raise DataError('RETURNED_DATA_DOES_NOT_MATCH_PLAN')


def run_plan(plan, *, db_path, collector=collect, wyckoff=None, smc=None):
    """Fetch once; validate and persist BEFORE either independent agent starts."""
    # Validate even a directly constructed plan; don't trust the dataclass label.
    checked = propose_source(venue=plan.venue, market=plan.market, symbol=plan.symbol,
        intent=plan.intent, requested_symbols=(plan.symbol,))
    if plan.proposed_by != checked.proposed_by or plan.scope_reason not in ('EXPLICIT_USER_REQUEST', 'SELECTED_PORTFOLIO_INSTRUMENT'):
        raise DataError('INVALID_PLAN_PROVENANCE')
    snapshot = collector(plan.symbol, plan.market)
    _check_binding(plan, snapshot)
    snapshot_id = digest(snapshot)
    with sqlite3.connect(db_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS market_snapshots (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO market_snapshots VALUES (?, ?)', (snapshot_id, canonical(snapshot)))
    outputs = {}
    for name, agent in [('wyckoff', wyckoff or WyckoffAgent()), ('smc', smc or SMCAgent())]:
        try:
            # Each invocation gets its own copy of the same canonical snapshot.
            result = agent.run(json.loads(canonical(snapshot)))
            if result.get('snapshot_sha256') != snapshot_id:
                raise DataError('AGENT_SNAPSHOT_MISMATCH')
            outputs[name] = result
        except Exception as exc:
            outputs[name] = {'agent_id': agent.agent_id, 'snapshot_sha256': snapshot_id,
                'status': 'UNKNOWN', 'evidence': None, 'error': type(exc).__name__}
    return {'schema': 'decision-check.independent-agents.v1', 'plan': asdict(plan),
        'snapshot_sha256': snapshot_id, 'agents': outputs,
        'tapeout': {'status': 'NOT_REQUESTED', 'circuit_id': None}}
