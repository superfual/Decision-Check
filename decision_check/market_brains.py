"""Independent v2 brains. Deterministic heuristics, not calibrated probabilities.

Pinned vendor algorithms are unchanged; timeframe-neutral Wyckoff primitives
are applied directly to the selected series, never relabelled as 4H data.
"""
from copy import deepcopy
from dataclasses import asdict
from .market import digest, DataError
from .profile_data import PROFILES, validate_profile_snapshot
from .vendor.market_data import normalize_klines, MarketData
from .vendor import wyckoff as w
from .vendor.smc import analyze_smc

RULESET='decision-check.market-rules.v2'
UPSTREAM='ca6dce03685317e980d435d22539cc8d0bf45e15'


def check(key, passed, evidence):
    return {'rule':key,'pass':bool(passed),'evidence':evidence}


def context(rows):
    closes=[float(x[4]) for x in rows]
    fast=sum(closes[-20:])/20;slow=sum(closes[-50:])/50
    direction='BULLISH' if closes[-1]>fast>slow else 'BEARISH' if closes[-1]<fast<slow else 'NEUTRAL'
    return {'bias':direction,'last_close':closes[-1],'sma20':fast,'sma50':slow,
        'rule':'close > SMA20 > SMA50; reverse for bearish; otherwise neutral'}


def wyckoff_series(candles):
    tr=w.detect_trading_range(candles,lookback=30)
    if tr is None:
        return {'bias':'NEUTRAL','phase':'NO_RANGE','trading_range':None,'events':[],
            'confidence_score':20,'interpretation':'No stable recent range under the published heuristic.'}
    events=w._detect_climaxes(candles,tr)
    for detector in (w._detect_automatic_reactions,w._detect_secondary_tests,w._detect_springs_upthrusts,
                     w._detect_post_sweep_tests,w._detect_sos_sow,w._detect_lps_lpsy):
        events=w._dedupe_events(events+detector(candles,tr,events))
    bias,phase,score,interpretation=w._infer_bias_phase(events,candles,tr)
    return {'bias':{'ACCUMULATION':'BULLISH','DISTRIBUTION':'BEARISH'}.get(bias,bias),
        'phase':phase,'trading_range':asdict(tr),'events':[asdict(e) for e in events],
        'confidence_score':score,'interpretation':interpretation}


def wyckoff_rules(evidence, candles, ctx, side):
    codes=['SC','AR','ST','SPRING','SOS'] if side=='BULLISH' else ['BC','AR_DOWN','UT_TEST','UTAD','SOW']
    selected=[];after=-1
    for code in codes:
        matches=[e for e in evidence['events'] if e['code']==code and e['index']>after]
        if not matches: break
        event=min(matches,key=lambda e:e['index']);selected.append(event);after=event['index']
    ordered=len(selected)==len(codes)
    fresh=ordered and len(candles)-1-selected[-1]['index']<=10
    sweep=selected[3] if len(selected)>3 else None
    intact=bool(sweep) and all((c.close>sweep['price'] if side=='BULLISH' else c.close<sweep['price']) for c in candles[sweep['index']+1:])
    opposite='BEARISH' if side=='BULLISH' else 'BULLISH'
    return [check('stable_range',evidence['trading_range'] is not None,evidence['trading_range']),
        check('ordered_event_sequence',ordered,selected),check('confirmation_within_10_bars',fresh,selected[-1:] if ordered else []),
        check('sweep_extreme_not_closed_through',intact,sweep),
        check('higher_timeframe_not_opposed',ctx['bias']!=opposite,ctx),
        check('wyckoff_bias_same_direction',evidence['bias']==side,evidence['bias'])]


def smc_rules(evidence, candles, ctx, side):
    # A historical sweep alone is insufficient: require a later close-confirmed
    # break, a displacement zone linked to that break, and an unbroken extreme.
    candidates=[]
    for sweep in evidence['liquidity_sweeps']:
        if sweep['direction']!=side:continue
        for event in evidence['events']:
            if event['direction']!=side or event['confirmation']!='CLOSE' or event['index']<=sweep['index']:continue
            zones=[z for z in evidence['order_blocks'] if z['direction']==side and z['source_event_index']==event['index']
                and z['status'] in ('FRESH','TOUCHED')]
            if zones:candidates.append((sweep,event,zones))
    chosen=max(candidates,key=lambda x:x[1]['index']) if candidates else None
    sweep,event,zones=chosen if chosen else (None,None,[])
    fresh=bool(event) and len(candles)-1-event['index']<=10
    intact=bool(sweep) and all((c.close>sweep['extreme_price'] if side=='BULLISH' else c.close<sweep['extreme_price']) for c in candles[sweep['index']+1:])
    opposite='BEARISH' if side=='BULLISH' else 'BULLISH'
    return [check('sweep_before_close_confirmed_break',bool(chosen),{'sweep':sweep,'break':event}),
        check('linked_active_displacement_order_block',bool(zones),zones),
        check('break_within_10_bars',fresh,event),check('sweep_extreme_not_closed_through',intact,sweep),
        check('latest_structure_same_direction',evidence['bias']==side,evidence['trend_state']),
        check('higher_timeframe_not_opposed',ctx['bias']!=opposite,ctx)]


class MarketBrain:
    name=None
    def run(self,snapshot):
        try:
            s=deepcopy(snapshot);validate_profile_snapshot(s)
            p=PROFILES[s['profile']];tf=p[self.name];candles=normalize_klines(s['bars'][tf])
            ctx=context(s['bars'][p['context']])
            if self.name=='wyckoff':
                evidence=wyckoff_series(candles);rules=wyckoff_rules
            else:
                mapping={'1d':'daily','4h':'four_hour','1h':'one_hour','15m':'fifteen_minute'}
                market=MarketData(s['symbol'],candles[-1].close,[],[],[],[])
                setattr(market,mapping[tf],candles)
                evidence=asdict(analyze_smc(market,timeframe=tf));rules=smc_rules
                if evidence['errors']:raise DataError('UPSTREAM_DATA_REJECTED')
            evidence['symbol']=s['symbol'];evidence['errors']=[]
            directions={}
            for side in ('BULLISH','BEARISH'):
                checks=rules(evidence,candles,ctx,side)
                directions[side]={'pass':all(c['pass'] for c in checks),'checks':checks}
            conflict=all(d['pass'] for d in directions.values())
            if conflict:
                for d in directions.values(): d['pass']=False
            return {'schema':'decision-check.market-brain.v2','agent_id':'decision-check.'+self.name+'.v2',
                'ruleset':RULESET,'upstream_revision':UPSTREAM,'status':'ANALYZED',
                'snapshot_sha256':digest(s),'scope':{k:s[k] for k in ('venue','symbol','market','profile','cutoff_ms','kind')},
                'analysis_timeframe':tf,'context_timeframe':p['context'],'context':ctx,'evidence':evidence,
                'directions':directions,'conflict':conflict,'valid':not conflict,
                'risk_scenario_candidates': {'source':'OBSERVED_LEVELS_NOT_PRICE_FORECASTS',
                    'range':evidence.get('trading_range'),
                    'latest_swing_high':evidence.get('latest_swing_high'),
                    'latest_swing_low':evidence.get('latest_swing_low'),
                    'usage':'Candidate invalidation levels only; user selects horizon and scenario. No probability assigned.'},
                'interpretation_scope':'Heuristic scenario evidence; scores are not calibrated probabilities.',
                'tapeout':{'status':'NOT_REQUESTED','circuit_id':None}}
        except (DataError,KeyError,TypeError,ValueError,OverflowError,AttributeError) as exc:
            return {'schema':'decision-check.market-brain.v2','agent_id':'decision-check.'+self.name+'.v2',
                'ruleset':RULESET,'status':'UNKNOWN','valid':False,'errors':[str(exc)],
                'directions':{'BULLISH':{'pass':None},'BEARISH':{'pass':None}},
                'tapeout':{'status':'NOT_REQUESTED','circuit_id':None}}


class WyckoffBrain(MarketBrain):
    name='wyckoff'


class SMCBrain(MarketBrain):
    name='smc'


def run_market_brains(snapshot):
    # No agent consumes the other's output. Both receive isolated identical data.
    return {'schema':'decision-check.market-pair.v2','wyckoff':WyckoffBrain().run(snapshot),
        'smc':SMCBrain().run(snapshot),'tapeout':{'status':'NOT_REQUESTED','circuit_id':None}}
