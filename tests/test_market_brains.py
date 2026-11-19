import copy,json,math,unittest
from datetime import datetime,timezone
from unittest.mock import patch
from decision_check.market import DataError,digest
from decision_check.profile_data import PROFILES,DELTAS,next_open,bars_at_cutoff,validate_profile_snapshot,collect_profile
from decision_check.market_brains import WyckoffBrain,SMCBrain,run_market_brains,wyckoff_rules,smc_rules
from decision_check.vendor.market_data import Candle
from decision_check.decision_logic import evaluate_three,boolean_gate
from test_portfolio_insider import bnb


def snapshot(profile='SWING'):
    cutoff=int(datetime(2026,11,19,tzinfo=timezone.utc).timestamp()*1000)
    bars={}
    for tf,count in PROFILES[profile]['counts'].items():
        if tf=='1M':
            d=datetime(2026,11,1,tzinfo=timezone.utc);opens=[]
            for _ in range(count):
                d=datetime(d.year-(d.month==1),(d.month-2)%12+1,1,tzinfo=timezone.utc)
                opens.append(int(d.timestamp()*1000))
            opens.reverse()
        else:
            delta=DELTAS[tf];offset=345600000 if tf=='1w' else 0
            last=((cutoff-offset)//delta-1)*delta+offset
            opens=[last-(count-1-i)*delta for i in range(count)]
        rows=[]
        for i,o in enumerate(opens):
            c=100+math.sin(i*.6)*3
            rows.append([o,str(c-.2),str(c+1),str(c-1),str(c),'100',next_open(o,tf)-1])
        bars[tf]=rows
    return {'schema':'decision-check.profile-snapshot.v1','venue':'BINANCE','market':'SPOT','symbol':'BNBUSDT',
        'profile':profile,'cutoff_ms':cutoff,'source':'https://data-api.binance.vision/api/v3/klines',
        'kind':'SYNTHETIC_TEST','bars':bars}


class MarketBrainTests(unittest.TestCase):
    def test_profiles_calendar_and_independence(self):
        for profile in PROFILES:
            s=snapshot(profile);before=copy.deepcopy(s);validate_profile_snapshot(s)
            pair=run_market_brains(s)
            for key in ('wyckoff','smc'):
                r=pair[key];self.assertEqual(r['status'],'ANALYZED',r)
                self.assertEqual(r['snapshot_sha256'],digest(s))
                self.assertEqual(r['analysis_timeframe'],PROFILES[profile][key])
                self.assertFalse(any(x['pass'] for x in r['directions'].values()))
            self.assertEqual(s,before)
            self.assertEqual(pair,run_market_brains(s))

    def test_invalid_candles_block_both_no_false_pass(self):
        for mutation in ('gap','future','nan','wrongsource','count','stale','duplicate','alignment'):
            s=snapshot();rows=s['bars']['1h']
            if mutation=='gap':rows[100][0]+=3600000;rows[100][6]+=3600000
            if mutation=='future':rows[-1][0]+=3600000;rows[-1][6]+=3600000
            if mutation=='nan':rows[-1][4]='NaN'
            if mutation=='wrongsource':s['market']='USD_M_FUTURES'
            if mutation=='count':rows.pop()
            if mutation=='stale':s['cutoff_ms']+=3600000
            if mutation=='duplicate':rows[-1]=rows[-2]
            if mutation=='alignment':rows[-1][0]+=1
            with self.subTest(mutation=mutation):
                r=run_market_brains(s)
                for agent in ('wyckoff','smc'):
                    self.assertEqual(r[agent]['status'],'UNKNOWN')
                    self.assertIsNone(r[agent]['directions']['BULLISH']['pass'])

    def test_calendar_months_and_leap_year(self):
        opened=int(datetime(2024,2,1,tzinfo=timezone.utc).timestamp()*1000)
        ended=int(datetime(2024,3,1,tzinfo=timezone.utc).timestamp()*1000)
        self.assertEqual(next_open(opened,'1M'),ended)
        with self.assertRaises(DataError):next_open(opened+86400000,'1M')

    def test_collector_one_clock_and_exact_profile_scope(self):
        s=snapshot();calls=[]
        from urllib.parse import urlparse,parse_qs
        def request(url):
            calls.append(url)
            if url.endswith('/time'):return {'serverTime':s['cutoff_ms']}
            q=parse_qs(urlparse(url).query)
            self.assertEqual(q['symbol'],['BNBUSDT'])
            return s['bars'][q['interval'][0]]
        got=collect_profile('BNBUSDT',request=request)
        self.assertEqual(got['kind'],'OBSERVED');self.assertEqual(len(calls),4)
        with self.assertRaises(DataError):collect_profile('BNBUSDT',market='OPTIONS',request=request)

    def test_wyckoff_order_recency_and_context(self):
        candles=[Candle(i,100,110,90,100,100) for i in range(41)]
        e={'bias':'BULLISH','trading_range':{'support':95},'events':[{'code':code,'index':i+25,'price':90} for i,code in enumerate(['SC','AR','ST','SPRING','SOS'])]}
        ctx={'bias':'NEUTRAL'}
        self.assertTrue(all(c['pass'] for c in wyckoff_rules(e,candles[:39],ctx,'BULLISH')))
        self.assertFalse(all(c['pass'] for c in wyckoff_rules(e,candles,ctx,'BULLISH')))
        self.assertFalse(all(c['pass'] for c in wyckoff_rules(e,candles[:39],{'bias':'BEARISH'},'BULLISH')))
        e['events'][2]['index']=39
        self.assertFalse(all(c['pass'] for c in wyckoff_rules(e,candles,ctx,'BULLISH')))

    def test_smc_sequence_zone_lifecycle_and_wrong_direction(self):
        candles=[Candle(i,100,110,90,100,100) for i in range(41)]
        e={'liquidity_sweeps':[{'direction':'BULLISH','index':30,'extreme_price':90}],
            'events':[{'direction':'BULLISH','confirmation':'CLOSE','index':32}],
            'order_blocks':[{'direction':'BULLISH','source_event_index':32,'status':'FRESH'}],
            'bias':'BULLISH','trend_state':'BULLISH_CONTINUATION'}
        self.assertTrue(all(c['pass'] for c in smc_rules(e,candles,{'bias':'NEUTRAL'},'BULLISH')))
        e['order_blocks'][0]['status']='INVALIDATED'
        self.assertFalse(all(c['pass'] for c in smc_rules(e,candles,{'bias':'NEUTRAL'},'BULLISH')))
        e['order_blocks'][0]['status']='FRESH';e['events'][0]['index']=29
        self.assertFalse(all(c['pass'] for c in smc_rules(e,candles,{'bias':'NEUTRAL'},'BULLISH')))

    def test_three_legs_fail_closed_scope_and_requested_budget(self):
        p=bnb();s=snapshot();r=evaluate_three(p,s,evaluated_at='2026-11-19T00:00:00Z')
        self.assertEqual(r['status'],'RULES_NOT_MET')
        self.assertFalse(r['circuit_candidate']['bits']['portfolio_pass'])
        self.assertFalse(r['circuit_candidate']['local_result'])
        p['decision']['symbol']='BTCUSDT'
        self.assertEqual(evaluate_three(p,s,evaluated_at='2026-11-19T00:00:00Z')['status'],'UNKNOWN')
        p=bnb();p['as_of']='2026-11-19T02:00:00Z'
        self.assertEqual(evaluate_three(p,s,evaluated_at='2026-11-19T00:00:00Z')['status'],'UNKNOWN')

    def test_combiner_all_64_boolean_cases(self):
        import itertools
        keys=('wyckoff_valid','wyckoff_pass','smc_valid','smc_pass','portfolio_valid','portfolio_pass')
        for values in itertools.product((False,True),repeat=6):
            self.assertEqual(boolean_gate(dict(zip(keys,values))),all(values))
        with self.assertRaises(ValueError):boolean_gate(dict(zip(keys,[1]*6)))

    def test_one_agent_exception_does_not_change_other(self):
        s=snapshot();expected=SMCBrain().run(s)
        with patch('decision_check.market_brains.wyckoff_series',side_effect=ValueError('test')):
            pair=run_market_brains(s)
        self.assertEqual(pair['wyckoff']['status'],'UNKNOWN')
        self.assertEqual(pair['smc'],expected)

if __name__=='__main__':unittest.main()
