import copy
from decimal import Decimal as D
import json
from pathlib import Path
import unittest
from decision_check.portfolio_insider import PortfolioInsiderAgent


def bnb(cost='400'):
    return {'schema':'portfolio-insider.input.v1','as_of':'2026-11-19T00:00:00Z',
        'reporting_currency':'USD','data_source':'SELF_REPORTED',
        'portfolio':{'cash':[{'id':'cash-usd','asset':'USD','amount':'700','available_amount':'700','fx_rate':'1'}],
            'spot':[{'id':'bnb','asset':'BNB','venue':'Binance','quantity':'0.5','price':'600','cost_basis':cost}],
            'futures_accounts':[],'futures':[]},
        'decision':{'product':'SPOT','intent':'ADD_SPOT','asset':'BNB','symbol':'BNBUSDT','venue':'Binance',
            'position_id':'bnb','funding_id':'cash-usd','profile':'SWING','holding_horizon':'one month',
            'proposed_amount':'100','loss_tolerance_pct':'10','entry_price':'600',
            'stop_or_scenario_price':'500','cycle_price':'300'},
        'cycle':{'anchor_id':'cycle-2026-11','anchor_as_of':'2026-11-19T00:00:00Z',
            'anchor_nav':'1000','max_loss_pct':'20','external_flows_reconciled':True,'prices':{'bnb':'300'}}}


def futures(direction='LONG'):
    short=direction=='SHORT'
    x=bnb();x['portfolio']={'cash':[],'spot':[],
        'futures_accounts':[{'id':'futures','settlement_asset':'USDT','wallet_balance':'1000','available_margin':'1000','fx_rate':'1'}],
        'futures':[]}
    x['decision'].update(product='LINEAR_FUTURES',intent='OPEN_FUTURES',direction=direction,
        position_id=None,funding_id='futures',leverage='10',
        stop_or_scenario_price='700' if short else '500',cycle_price='900' if short else '300')
    x['cycle']['prices']={}
    return x


class BrainTests(unittest.TestCase):
    def run_brain(self,x):
        r=PortfolioInsiderAgent().run(x)
        self.assertEqual(r['status'],'ANALYTICAL_REVIEW_ONLY',r)
        return r

    def cash_case(self):
        x=bnb();x['decision'].update(proposed_amount='600',loss_tolerance_pct='90',stop_or_scenario_price='590',minimum_cash_pct='20')
        x['cycle']['max_loss_pct']='99'
        return x

    def test_cash_ratio_caps_purchase_at_selected_percentage(self):
        r=self.run_brain(self.cash_case())
        self.assertEqual(D(r['sizing']['caps']['cash_safety']),500)
        self.assertEqual(D(r['sizing']['bounded_amount']),500)
        self.assertFalse(r['requested']['gates']['cash_safety'])
        self.assertTrue(r['bounded']['gates']['cash_safety'])
        self.assertEqual(D(r['bounded']['cash_ratio_after_purchase_pct']),20)

    def test_cash_ratio_is_adjustable_and_not_fixed_at_twenty(self):
        x=self.cash_case();x['decision']['minimum_cash_pct']='30'
        self.assertEqual(D(self.run_brain(x)['sizing']['caps']['cash_safety']),400)
        x['decision']['minimum_cash_pct']='10'
        self.assertEqual(D(self.run_brain(x)['sizing']['caps']['cash_safety']),600)

    def test_existing_cash_below_target_allows_no_additional_purchase(self):
        x=self.cash_case();x['decision']['minimum_cash_pct']='80'
        r=self.run_brain(x)
        self.assertEqual(D(r['sizing']['bounded_amount']),0)
        self.assertFalse(r['bounded']['gates']['cash_safety'])

    def test_cash_ratio_accounts_for_fee_buffer_and_invalid_percent(self):
        x=self.cash_case();x['decision']['loss_buffer_pct']='1'
        r=self.run_brain(x)
        self.assertGreaterEqual(D(r['bounded']['cash_ratio_after_purchase_pct']),20)
        self.assertLess(D(r['sizing']['bounded_amount']),500)
        x['decision']['minimum_cash_pct']='101'
        self.assertNotEqual(PortfolioInsiderAgent().run(x)['status'],'ANALYTICAL_REVIEW_ONLY')

    def test_limit_fill_is_hypothetical_and_preserves_current_nav(self):
        x=bnb();x['decision'].update(entry_mode='LIMIT',entry_price='550',stop_or_scenario_price='450')
        r=self.run_brain(x)
        self.assertEqual(D(r['current']['nav']),1000)
        self.assertEqual(x['portfolio']['spot'][0]['price'],'600')
        x['decision']['entry_mode']='MARKET'
        r=PortfolioInsiderAgent().run(x)
        self.assertNotEqual(r['status'],'ANALYTICAL_REVIEW_ONLY')

    def test_bnb_dca_negative_and_two_gates(self):
        r=self.run_brain(bnb())
        self.assertEqual(D(r['current']['nav']),1000)
        p=r['current']['positions'][0]
        self.assertEqual(D(p['average_cost']),800)
        self.assertEqual(D(p['unrealized_pnl']),-100)
        self.assertEqual(D(p['pnl_pct_of_cost']),-25)
        self.assertEqual(D(r['risk_contract']['decision_loss_budget_frozen']),10)
        self.assertEqual(D(r['sizing']['caps']['cycle']),100)
        self.assertEqual(D(r['sizing']['bounded_amount']),60)
        self.assertFalse(r['requested']['gates']['decision'])
        self.assertTrue(r['requested']['gates']['cycle'])
        bounded=r['bounded'];self.assertEqual(D(bounded['decision_loss']),10)
        self.assertEqual(D(bounded['cycle_scenario_nav']),820)
        self.assertEqual(D(bounded['cycle_drawdown_pct_from_anchor']),18)
        self.assertEqual(D(bounded['spot_after']['unrealized_pnl']),-100)
        self.assertEqual(D(bounded['spot_after']['cycle_unrealized_pnl']),-280)
        self.assertEqual(bounded['spot_after']['state'],'DCA_NEGATIVE')
        self.assertTrue(bounded['risk_limits_met'])

    def test_dca_positive_same_exposure_same_forward_risk(self):
        n,p=self.run_brain(bnb()),self.run_brain(bnb('200'))
        self.assertEqual(p['bounded']['spot_after']['state'],'DCA_POSITIVE')
        self.assertEqual(D(p['current']['positions'][0]['unrealized_pnl']),100)
        self.assertEqual(n['sizing'],p['sizing'])
        self.assertEqual(n['bounded']['cycle_scenario_nav'],p['bounded']['cycle_scenario_nav'])
        self.assertEqual(D(p['bounded']['spot_after']['cycle_unrealized_pnl']),-80)

    def test_nav_anchor_is_not_reset_after_losses(self):
        x=bnb();x['portfolio']['cash'][0].update(amount='500',available_amount='500')
        r=self.run_brain(x)
        self.assertEqual(D(r['current']['nav']),800)
        self.assertEqual(D(r['risk_contract']['cycle_anchor_nav']),1000)
        self.assertEqual(D(r['sizing']['bounded_amount']),0)
        self.assertFalse(r['bounded']['gates']['cycle'])

    def test_loss_budget_not_rebased_to_resized_purchase(self):
        r=self.run_brain(bnb())
        self.assertEqual(D(r['risk_contract']['decision_loss_budget_frozen']),10)
        self.assertEqual(D(r['bounded']['decision_loss_pct_of_requested']),10)
        self.assertNotEqual(D(r['bounded']['decision_loss']),D('60')*D('.1'))

    def test_scale_invariance(self):
        a=bnb();b=copy.deepcopy(a)
        b['portfolio']['cash'][0].update(amount='7000',available_amount='7000')
        b['portfolio']['spot'][0].update(quantity='5',cost_basis='4000')
        b['decision']['proposed_amount']='1000';b['cycle']['anchor_nav']='10000'
        ra,rb=self.run_brain(a),self.run_brain(b)
        self.assertEqual(ra['current']['cash_pct'],rb['current']['cash_pct'])
        self.assertEqual(ra['bounded']['cycle_drawdown_pct_from_anchor'],rb['bounded']['cycle_drawdown_pct_from_anchor'])
        self.assertEqual(D(rb['sizing']['bounded_amount']),D(ra['sizing']['bounded_amount'])*10)

    def test_cash_stablecoins_explicit_fx_and_available(self):
        x=bnb();x['portfolio']['cash']=[{'id':'cash-usd','asset':'USDT','amount':'700','available_amount':'300','fx_rate':'0.9'}]
        r=self.run_brain(x)
        self.assertEqual(D(r['current']['cash_value']),630)
        self.assertEqual(D(r['current']['available_cash']),270)
        self.assertEqual(r['current']['cash_buckets'][0]['asset'],'USDT')

    def test_missing_cost_is_unknown_not_zero(self):
        x=bnb(None);r=self.run_brain(x)
        self.assertIsNone(r['current']['spot_unrealized_pnl'])
        self.assertIsNone(r['bounded']['spot_after']['average_cost'])
        self.assertEqual(r['bounded']['spot_after']['state'],'UNKNOWN_COST_BASIS')

    def test_entire_portfolio_scenario_required(self):
        x=bnb();x['portfolio']['spot'].append({'id':'btc','asset':'BTC','venue':'Binance','quantity':'1','price':'100','cost_basis':'90'})
        r=PortfolioInsiderAgent().run(x)
        self.assertEqual(r['status'],'NEEDS_DATA_OR_UNSUPPORTED')
        self.assertIn('SCENARIO_REQUIRES_EVERY_POSITION_EXACTLY',r['errors'][0])

    def test_allocated_budget_limits_multiple_decisions(self):
        x=bnb();x['decision']['allocated_loss_budget']='5'
        r=self.run_brain(x)
        self.assertEqual(D(r['sizing']['bounded_amount']),30)
        self.assertEqual(D(r['risk_contract']['decision_loss_budget_frozen']),5)

    def test_long_and_short_futures_and_leverage(self):
        for side in ['LONG','SHORT']:
            x=futures(side);r=self.run_brain(x)
            self.assertEqual(D(r['sizing']['bounded_amount']),60)
            self.assertEqual(D(r['bounded']['quantity']),D('.1'))
            self.assertEqual(D(r['bounded']['decision_loss']),10)
            self.assertEqual(D(r['bounded']['estimated_initial_margin_quote']),6)
            self.assertEqual(r['bounded']['futures_after']['stop_status'],'HYPOTHETICAL_NOT_PLACED')
            self.assertEqual(r['bounded']['futures_after']['margin_safety'],'UNKNOWN_NOT_A_LIQUIDATION_CHECK')
            x['decision']['leverage']='2';r2=self.run_brain(x)
            self.assertEqual(r['bounded']['decision_loss'],r2['bounded']['decision_loss'])
            self.assertEqual(D(r2['bounded']['estimated_initial_margin_quote']),30)

    def test_futures_equity_counts_wallet_once_and_hedge_net(self):
        x=futures();x['portfolio']['futures_accounts'][0]['wallet_balance']='800'
        x['portfolio']['spot']=[{'id':'bnb','asset':'BNB','venue':'Binance','quantity':'0.5','price':'600','cost_basis':'400'}]
        x['portfolio']['futures']=[{'id':'short','account_id':'futures','asset':'BNB','venue':'Binance','contract_type':'LINEAR','direction':'SHORT','quantity':'0.5','entry_price':'400','mark_price':'600'}]
        x['cycle']['prices']={'bnb':'300','short':'300'}
        r=self.run_brain(x)
        self.assertEqual(D(r['current']['nav']),1000)
        self.assertEqual(D(r['current']['futures_unrealized_pnl']),-100)
        self.assertEqual(D(r['net_directional_exposure_pct_nav']['BNB']),0)
        self.assertEqual(D(r['hold_unchanged']['cycle_scenario_nav']),1000)

    def test_unknown_margin_cannot_pass_complete_gates(self):
        x=futures();x['portfolio']['futures_accounts'][0]['available_margin']=None
        r=self.run_brain(x)
        self.assertIsNone(r['bounded']['gates']['funding_or_margin_estimate'])
        self.assertFalse(r['bounded']['risk_limits_met'])

    def test_fee_buffer_reduces_size(self):
        x=bnb();x['decision']['loss_buffer_pct']='1'
        r=self.run_brain(x)
        self.assertLess(D(r['sizing']['bounded_amount']),60)
        self.assertLessEqual(D(r['bounded']['decision_loss']),10)

    def test_source_profile_and_pnl_no_execution_claims(self):
        r=self.run_brain(bnb())
        self.assertEqual(r['market_request']['requested_timeframes'],['1d','4h','1h'])
        self.assertEqual(r['market_evidence']['status'],'NOT_RUN')
        self.assertEqual(r['tapeout']['status'],'NOT_REQUESTED')
        self.assertIsNone(r['tapeout']['circuit_id'])

    def test_evidence_disagreement_and_wrong_snapshot(self):
        x=bnb();sha='a'*64
        x['market_evidence']={'plan':{'symbol':'BNBUSDT','venue':'Binance','market':'SPOT'},
            'profile':'SWING','cutoff_ms':'1795046400000','max_age_ms':'900000','snapshot_sha256':sha,
            'agents':{k:{'status':'ANALYZED','snapshot_sha256':sha,'evidence':{'symbol':'BNBUSDT','bias':bias,'errors':[]}} for k,bias in [('wyckoff','BULLISH'),('smc','BEARISH')]}}
        r=self.run_brain(x);self.assertEqual(r['market_evidence']['agreement'],'CONFLICT')
        x['market_evidence']['agents']['smc']['snapshot_sha256']='b'*64
        r=self.run_brain(x);self.assertEqual(r['market_evidence']['status'],'REJECTED')

    def test_invalid_or_unsupported_never_passes(self):
        variants=[]
        x=bnb();x['decision']['proposed_amount']='NaN';variants.append(x)
        x=bnb();x['decision']['stop_or_scenario_price']='700';variants.append(x)
        x=bnb();x['cycle']['external_flows_reconciled']=False;variants.append(x)
        x=bnb();x['portfolio']['cash'].append(copy.deepcopy(x['portfolio']['cash'][0]));variants.append(x)
        x=futures();x['portfolio']['futures']=[{'id':'inverse','contract_type':'INVERSE','direction':'LONG'}];variants.append(x)
        x=bnb();x['decision']['proposed_amount']=100.0;variants.append(x)
        for x in variants:
            with self.subTest(x=x):
                r=PortfolioInsiderAgent().run(x);self.assertEqual(r['status'],'NEEDS_DATA_OR_UNSUPPORTED');self.assertEqual(r['tapeout']['status'],'NOT_REQUESTED')

    def test_no_input_mutation_and_determinism(self):
        x=bnb();before=copy.deepcopy(x)
        a=self.run_brain(x);b=self.run_brain(x)
        self.assertEqual(a,b);self.assertEqual(x,before)

    def test_btc_initial_example(self):
        x=bnb();x['portfolio']['spot']=[];x['portfolio']['cash'][0].update(amount='1000',available_amount='1000')
        x['decision'].update(asset='BTC',symbol='BTCUSDT',intent='BUY_SPOT',position_id=None,
            proposed_amount='1000',loss_tolerance_pct='30',entry_price='65000',stop_or_scenario_price='50000',cycle_price='32500')
        x['cycle'].update(max_loss_pct='30',prices={})
        r=self.run_brain(x)
        self.assertEqual(D(r['sizing']['caps']['decision']),1300)
        self.assertEqual(D(r['sizing']['caps']['cycle']),600)
        self.assertEqual(D(r['sizing']['bounded_amount']),600)

if __name__=='__main__':unittest.main()
