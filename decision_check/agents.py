"""Independent deterministic analysis agents sharing validated source snapshots.

Neither agent receives the other's output or fetches its own market data.
They are analysis runners, not deployed TapeOut circuits or LLM services.
"""
from copy import deepcopy
from dataclasses import asdict
from .market import digest, validate_snapshot
from .vendor.market_data import build_market_data
from .vendor.wyckoff import analyze_wyckoff
from .vendor.smc import analyze_smc

UPSTREAM = 'ca6dce03685317e980d435d22539cc8d0bf45e15'


def _market(snapshot):
    validate_snapshot(snapshot)
    b = snapshot['bars']
    return build_market_data(snapshot['symbol'], b['15m'][-1][4],
        b['1d'], b['4h'], b['1h'], b['15m'])


class WyckoffAgent:
    agent_id = 'decision-check.wyckoff.v1'

    def run(self, snapshot):
        isolated = deepcopy(snapshot)
        evidence = analyze_wyckoff(_market(isolated))
        return {'agent_id': self.agent_id, 'upstream_revision': UPSTREAM,
            'snapshot_sha256': digest(isolated), 'status': 'UNKNOWN' if evidence.errors else 'ANALYZED',
            'evidence': asdict(evidence)}


class SMCAgent:
    agent_id = 'decision-check.smc.v1'

    def run(self, snapshot):
        isolated = deepcopy(snapshot)
        evidence = analyze_smc(_market(isolated), timeframe='1h')
        return {'agent_id': self.agent_id, 'upstream_revision': UPSTREAM,
            'snapshot_sha256': digest(isolated), 'status': 'UNKNOWN' if evidence.errors else 'ANALYZED',
            'evidence': asdict(evidence)}
