"""Three independent analytical legs -> explicit Boolean circuit candidates.

Recompute reports from source inputs. No deployment, wallet or transaction.
"""
from datetime import datetime
from decimal import Decimal
from .market import digest
from .market_brains import run_market_brains
from .portfolio_insider import PortfolioInsiderAgent


def evaluate_three(portfolio_input, snapshot):
    pair=run_market_brains(snapshot)
    portfolio=PortfolioInsiderAgent().run(portfolio_input)
    errors=[]
    try:
        d=portfolio_input['decision']
        market='SPOT' if d['product']=='SPOT' else 'USD_M_FUTURES'
        side='BEARISH' if d['product']=='LINEAR_FUTURES' and d['direction']=='SHORT' else 'BULLISH'
        if d['symbol'] != d['asset']+'USDT':errors.append('ASSET_SYMBOL_MISMATCH')
        if (d['symbol'],d['venue'].upper(),market,d['profile']) != (snapshot['symbol'],snapshot['venue'],snapshot['market'],snapshot['profile']):
            errors.append('SCOPE_MISMATCH')
        as_of=datetime.fromisoformat(portfolio_input['as_of'].replace('Z','+00:00'))
        if as_of.tzinfo is None: errors.append('TIMEZONE_REQUIRED')
        age=Decimal(str(as_of.timestamp()))*1000-snapshot['cutoff_ms']
        if age<0 or age>3600000:errors.append('SNAPSHOT_OUTSIDE_ONE_HOUR_WINDOW')
    except (KeyError,TypeError,ValueError,AttributeError):
        side='BULLISH';errors.append('INVALID_SCOPE_OR_TIME')
    w,s=pair['wyckoff'],pair['smc']
    bound=not errors
    wvalid=bound and w.get('valid',False) and w['status']=='ANALYZED'
    svalid=bound and s.get('valid',False) and s['status']=='ANALYZED'
    pvalid=bound and portfolio['status']=='ANALYTICAL_REVIEW_ONLY'
    # A hypothetical margin estimate cannot certify futures safety.
    futures=portfolio_input.get('decision',{}).get('product')=='LINEAR_FUTURES'
    if futures: pvalid=False;errors.append('FUTURES_MARGIN_AND_LIQUIDATION_UNVERIFIED')
    wp=w['directions'][side]['pass'] if wvalid else None
    sp=s['directions'][side]['pass'] if svalid else None
    pp=portfolio['requested']['risk_limits_met'] if pvalid else None
    bits={'wyckoff_valid':wvalid,'wyckoff_pass':wp is True,
          'smc_valid':svalid,'smc_pass':sp is True,
          'portfolio_valid':pvalid,'portfolio_pass':pp is True}
    valid=wvalid and svalid and pvalid
    passed=boolean_gate(bits)
    return {'schema':'decision-check.three-logic.v1','status':'RULES_MET' if passed else 'RULES_NOT_MET' if valid else 'UNKNOWN',
        'side':side,'binding_errors':errors,'market_agents':pair,'portfolio':portfolio,
        'circuit_candidate':{'schema':'decision-check.boolean-inputs.v1','bits':bits,
            'rule':'W_valid AND W_pass AND S_valid AND S_pass AND P_valid AND P_pass',
            'local_result':passed,'data_valid':valid,
            'scope':'Requested amount only; bounded alternative is not silently approved.',
            'numeric_checks':portfolio.get('tapeout',{}).get('candidate_checks',[]),
            'status':'LOCAL_SIMULATION_NOT_DEPLOYED','circuit_id':None},
        'input_sha256':{'portfolio':digest(portfolio_input),'market':digest(snapshot)},
        'limitations':['OHLCV heuristic agreement is not proof of market truth or future profit.',
            'User-supplied account scope and market source are not authenticated.',
            'No orders, account connection, deployment or TapeOut evaluation.']}


def boolean_gate(bits):
    """Reference truth table for the six-bit combiner. Strict booleans only."""
    keys=('wyckoff_valid','wyckoff_pass','smc_valid','smc_pass','portfolio_valid','portfolio_pass')
    if set(bits)!=set(keys) or any(type(bits[k]) is not bool for k in keys):
        raise ValueError('SIX_BOOLEAN_INPUTS_REQUIRED')
    def nand(a,b): return not (a and b)
    # Six-input AND composed only of two-input NAND gates (10 gates).
    acc=bits[keys[0]]
    for key in keys[1:]:
        neg=nand(acc,bits[key]);acc=nand(neg,neg)
    return acc
