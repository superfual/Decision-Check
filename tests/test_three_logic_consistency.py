import copy
from datetime import datetime, timezone
from pathlib import Path
import unittest
from unittest.mock import patch
from test_market_brains import snapshot
from test_portfolio_insider import bnb
from decision_check.decision_logic import evaluate_three
from decision_check.portfolio_insider import PortfolioInsiderAgent

class ThreeLogicConsistencyTests(unittest.TestCase):
    def run_case(self, data=None, stamp='2026-11-19T00:01:07Z', **kw):
        s=snapshot();s['cutoff_ms']=int(datetime.fromisoformat(stamp.replace('Z','+00:00')).timestamp()*1000)
        return evaluate_three(data or bnb(),s,evaluated_at='2026-11-19T00:02:00Z',**kw)

    def test_market_collection_after_portfolio_is_valid(self):
        r=self.run_case();self.assertEqual(r['binding_errors'],[])
        self.assertEqual(r['status'],'RULES_NOT_MET')
        self.assertEqual(r['timing']['mode'],'RECORDED_REPLAY')

    def test_stale_and_future_timestamps_fail_closed(self):
        for stamp,error in [('2026-11-18T22:59:00Z','MARKET_OLDER_THAN_ONE_HOUR'),('2026-11-19T00:03:00Z','MARKET_TIMESTAMP_IN_FUTURE')]:
            with self.subTest(stamp=stamp):
                r=self.run_case(stamp=stamp);self.assertIn(error,r['binding_errors']);self.assertEqual(r['status'],'UNKNOWN')
        p=bnb();p['as_of']='2026-11-18T22:59:00Z';self.assertIn('PORTFOLIO_OLDER_THAN_ONE_HOUR',self.run_case(p)['binding_errors'])
        p['as_of']='2026-11-19T00:03:00Z';self.assertIn('PORTFOLIO_TIMESTAMP_IN_FUTURE',self.run_case(p)['binding_errors'])

    def test_cash_safety_survives_recomputation_and_blocks_purchase(self):
        p=bnb();p['decision'].update(minimum_cash_pct='65',loss_tolerance_pct='50')
        standalone=PortfolioInsiderAgent().run(p);combined=self.run_case(p)['portfolio']
        self.assertEqual(standalone,combined)
        self.assertFalse(combined['requested']['gates']['cash_safety'])
        self.assertFalse(combined['requested']['risk_limits_met'])
        self.assertEqual(combined['sizing']['caps']['cash_safety'],'50')

    def test_engine_mismatch_and_missing_check_fail_closed(self):
        r=self.run_case(expected_portfolio_version='old-engine');self.assertIn('PORTFOLIO_ENGINE_VERSION_MISMATCH',r['binding_errors']);self.assertEqual(r['status'],'UNKNOWN')
        report=PortfolioInsiderAgent().run(bnb());del report['requested']['gates']['cash_safety']
        with patch('decision_check.decision_logic.PortfolioInsiderAgent.run',return_value=report):
            self.assertIn('PORTFOLIO_RISK_CHECKS_INCOMPLETE',self.run_case()['binding_errors'])

    def test_generated_browser_modules_match_canonical_sources(self):
        root=Path(__file__).resolve().parents[1]
        for rel in ['portfolio_insider/brain.py','decision_logic.py']:
            self.assertEqual((root/'decision_check'/rel).read_bytes(),(root/'site/market-runtime/decision_check'/rel).read_bytes())
        self.assertEqual((root/'decision_check/portfolio_insider/brain.py').read_bytes(),(root/'site/portfolio-brain/brain.py').read_bytes())
