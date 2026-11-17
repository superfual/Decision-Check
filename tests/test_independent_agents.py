import copy
import json
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock
from test_market_pipeline import snapshot
from decision_check.agents import WyckoffAgent, SMCAgent
from decision_check.intake import propose_source, run_plan
from decision_check.market import DataError, digest


class IndependentAgentsTests(unittest.TestCase):
    def plan(self, **kwargs):
        data = dict(venue='BINANCE', market='SPOT', symbol='BTCUSDT', intent='BUY_SPOT', requested_symbols=['BTCUSDT'])
        data.update(kwargs)
        return propose_source(**data)

    def test_explicit_scope_no_universe_scan(self):
        self.assertEqual(self.plan().scope_reason, 'EXPLICIT_USER_REQUEST')
        self.assertEqual(self.plan(requested_symbols=[], holding_symbols=['BTCUSDT']).scope_reason, 'SELECTED_PORTFOLIO_INSTRUMENT')
        with self.assertRaises(DataError): self.plan(requested_symbols=[])
        with self.assertRaises(DataError): self.plan(symbol='ETHUSDT')

    def test_no_venue_or_product_substitution(self):
        with self.assertRaises(DataError): self.plan(venue='OKX')
        with self.assertRaises(DataError): self.plan(market='USD_M_FUTURES')
        self.assertEqual(self.plan(market='USD_M_FUTURES', intent='REVIEW_FUTURES').market, 'USD_M_FUTURES')

    def test_data_gate_blocks_both_agents(self):
        for bad in ['invalid', 'wrong_symbol', 'missing']:
            data = snapshot()
            if bad == 'invalid': data['bars']['1h'].pop()
            if bad == 'wrong_symbol': data['symbol'] = 'ETHUSDT'
            w, s = Mock(), Mock()
            def collector(*_):
                if bad == 'missing': raise DataError('UNAVAILABLE')
                return data
            with self.subTest(case=bad), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(DataError): run_plan(self.plan(), db_path=tmp+'/db', collector=collector, wyckoff=w, smc=s)
                w.run.assert_not_called(); s.run.assert_not_called()

    def test_single_fetch_saved_before_agents_and_same_snapshot(self):
        data = snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            path=tmp+'/db'; collector=Mock(return_value=data)
            class Probe:
                agent_id='probe'
                def run(self, snap):
                    with sqlite3.connect(path) as db:
                        stored=json.loads(db.execute('SELECT payload FROM market_snapshots').fetchone()[0])
                    self_snapshot_id=digest(snap)
                    self_outer.assertEqual(stored, snap)
                    snap['symbol']='MUTATED'
                    return {'snapshot_sha256':self_snapshot_id,'status':'ANALYZED'}
            probe=Probe();probe.self_outer=self
            result=run_plan(self.plan(), db_path=path,collector=collector,wyckoff=probe,smc=SMCAgent())
            collector.assert_called_once_with('BTCUSDT','SPOT')
            self.assertEqual(result['agents']['smc']['status'],'ANALYZED')
            self.assertEqual(data['symbol'],'BTCUSDT')
            self.assertEqual(result['agents']['wyckoff']['snapshot_sha256'],result['agents']['smc']['snapshot_sha256'])

    def test_one_agent_failure_does_not_skip_other(self):
        class Broken:
            agent_id='broken'
            def run(self, _): raise RuntimeError('no result')
        with tempfile.TemporaryDirectory() as tmp:
            result=run_plan(self.plan(),db_path=tmp+'/db',collector=lambda *_:snapshot(),wyckoff=Broken())
        self.assertEqual(result['agents']['wyckoff']['status'],'UNKNOWN')
        self.assertEqual(result['agents']['smc']['status'],'ANALYZED')
        self.assertEqual(result['tapeout']['status'],'NOT_REQUESTED')

    def test_agents_independent_and_do_not_mutate_input(self):
        data=snapshot(); before=copy.deepcopy(data)
        w=WyckoffAgent().run(data);s=SMCAgent().run(data)
        self.assertEqual(data,before)
        self.assertNotEqual(w['agent_id'],s['agent_id'])
        self.assertEqual(w['snapshot_sha256'],s['snapshot_sha256'])

if __name__ == '__main__': unittest.main()
