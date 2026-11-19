"""Portfolio Insider analytical core. No network, credentials, orders or LLM calls.

All calculations use Decimal. Price scenarios are assumptions, not probabilities.
SPOT and linear futures are product-specific; inverse/options are rejected.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_DOWN, localcontext
from datetime import datetime
import hashlib
import json

VERSION = 'portfolio-insider.brain.v1.1'
ZERO, ONE, HUNDRED = Decimal(0), Decimal(1), Decimal(100)
PROFILES = {'CYCLE': ['1M', '1w', '1d'], 'SWING': ['1d', '4h', '1h'],
            'INTRADAY': ['4h', '1h', '15m']}


class PortfolioInputError(ValueError):
    pass


def dec(value, name, *, minimum=ZERO, maximum=Decimal('1e18')):
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (str, int, Decimal)):
        raise PortfolioInputError('INVALID_DECIMAL:' + name)
    try:
        n = Decimal(value)
    except InvalidOperation as exc:
        raise PortfolioInputError('INVALID_DECIMAL:' + name) from exc
    if not n.is_finite() or n < minimum or n > maximum or n.as_tuple().exponent < -18:
        raise PortfolioInputError('OUT_OF_RANGE:' + name)
    return n


def positive(value, name):
    n = dec(value, name)
    if n <= ZERO:
        raise PortfolioInputError('POSITIVE_REQUIRED:' + name)
    return n


def percent(value, name):
    return dec(value, name, maximum=HUNDRED)


def ratio(value, denominator):
    return value / denominator * HUNDRED if denominator else None


def text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise PortfolioInputError('TEXT_REQUIRED:' + name)
    return value


def iso(value, name):
    text(value, name)
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise PortfolioInputError('INVALID_TIME:' + name) from exc
    if d.tzinfo is None:
        raise PortfolioInputError('TIMEZONE_REQUIRED:' + name)
    return d


def serialize(value):
    if isinstance(value, Decimal):
        return format(value.normalize(), 'f') if value else '0'
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [serialize(v) for v in value]
    return value


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()).hexdigest()


def within(loss, budget):
    # Decimal recurring ratios can differ by a final precision digit only.
    return loss <= budget + max(ONE, abs(budget)) * Decimal('1e-40')


def _positions(portfolio):
    """Money in cash buckets and futures accounts must be disjoint."""
    ids, cash, spots, accounts, futures = set(), [], [], {}, []
    def unique(row):
        key = text(row['id'], 'id')
        if key in ids:
            raise PortfolioInputError('DUPLICATE_ID:' + key)
        ids.add(key)
        return key
    for row in portfolio.get('cash', []):
        key = unique(row)
        amount = dec(row['amount'], 'cash.amount')
        available = dec(row['available_amount'], 'cash.available_amount')
        if available > amount:
            raise PortfolioInputError('AVAILABLE_EXCEEDS_BALANCE')
        cash.append({'id': key, 'asset': text(row['asset'], 'cash.asset'),
            'amount': amount, 'available': available, 'fx': positive(row['fx_rate'], 'cash.fx_rate')})
    for row in portfolio.get('spot', []):
        key = unique(row)
        qty, price = dec(row['quantity'], 'spot.quantity'), positive(row['price'], 'spot.price')
        cost = None if row.get('cost_basis') is None else dec(row['cost_basis'], 'spot.cost_basis')
        if qty == ZERO and cost not in (None, ZERO):
            raise PortfolioInputError('COST_WITHOUT_HOLDINGS')
        spots.append({'id': key, 'asset': text(row['asset'], 'spot.asset'),
            'venue': text(row['venue'], 'spot.venue'), 'quantity': qty, 'price': price, 'cost': cost})
    for row in portfolio.get('futures_accounts', []):
        key = unique(row)
        accounts[key] = {'id': key, 'asset': text(row['settlement_asset'], 'settlement_asset'),
            'wallet': dec(row['wallet_balance'], 'wallet_balance'),
            'available': None if row.get('available_margin') is None else dec(row['available_margin'], 'available_margin'),
            'fx': positive(row['fx_rate'], 'futures.fx_rate')}
    for row in portfolio.get('futures', []):
        key = unique(row)
        if row['contract_type'] != 'LINEAR' or row['direction'] not in ('LONG', 'SHORT'):
            raise PortfolioInputError('UNSUPPORTED_CONTRACT_OR_DIRECTION')
        account = row['account_id']
        if account not in accounts:
            raise PortfolioInputError('MISSING_FUTURES_ACCOUNT')
        futures.append({'id': key, 'asset': text(row['asset'], 'futures.asset'),
            'venue': text(row['venue'], 'futures.venue'), 'account': account,
            'quantity': positive(row['quantity'], 'futures.quantity'),
            'entry': positive(row['entry_price'], 'entry_price'),
            'price': positive(row['mark_price'], 'mark_price'),
            'sign': ONE if row['direction'] == 'LONG' else -ONE,
            'direction': row['direction']})
    return cash, spots, accounts, futures


def _current(cash, spots, accounts, futures):
    cash_value = sum((c['amount'] * c['fx'] for c in cash), ZERO)
    spot_value = sum((s['quantity'] * s['price'] for s in spots), ZERO)
    future_pnl = {a: ZERO for a in accounts}
    for f in futures:
        future_pnl[f['account']] += f['sign'] * f['quantity'] * (f['price'] - f['entry'])
    equities = {a: (v['wallet'] + future_pnl[a]) * v['fx'] for a, v in accounts.items()}
    nav = cash_value + spot_value + sum(equities.values(), ZERO)
    if nav <= ZERO:
        raise PortfolioInputError('NONPOSITIVE_NAV')
    pnl_known = all(s['cost'] is not None for s in spots)
    spot_pnl = sum((s['quantity'] * s['price'] - s['cost'] for s in spots), ZERO) if pnl_known else None
    cost = sum((s['cost'] for s in spots), ZERO) if pnl_known else None
    return {'nav': nav, 'cash_value': cash_value,
        'cash_pct': ratio(cash_value, nav),
        'available_cash': sum((c['available'] * c['fx'] for c in cash), ZERO),
        'cash_buckets': [{'id': c['id'], 'asset': c['asset'], 'value': c['amount'] * c['fx'],
            'nav_pct': ratio(c['amount'] * c['fx'], nav),
            'available_value': c['available'] * c['fx']} for c in cash],
        'spot_unrealized_pnl': spot_pnl, 'spot_unrealized_pnl_pct_of_cost': ratio(spot_pnl, cost) if pnl_known else None,
        'futures_unrealized_pnl': sum((future_pnl[a] * accounts[a]['fx'] for a in accounts), ZERO),
        'futures_account_equity': equities,
        'positions': [{'id': s['id'], 'product': 'SPOT', 'asset': s['asset'],
            'quantity': s['quantity'], 'value': s['quantity'] * s['price'],
            'nav_pct': ratio(s['quantity'] * s['price'], nav),
            'cost_basis': s['cost'], 'average_cost': s['cost'] / s['quantity'] if s['cost'] is not None and s['quantity'] else None,
            'unrealized_pnl': s['quantity'] * s['price'] - s['cost'] if s['cost'] is not None else None,
            'pnl_pct_of_cost': ratio(s['quantity'] * s['price'] - s['cost'], s['cost']) if s['cost'] is not None else None}
            for s in spots] + [{'id': f['id'], 'product': 'LINEAR_FUTURES', 'asset': f['asset'],
            'direction': f['direction'], 'quantity': f['quantity'],
            'notional': f['quantity'] * f['price'] * accounts[f['account']]['fx'],
            'signed_exposure_pct_nav': ratio(f['sign'] * f['quantity'] * f['price'] * accounts[f['account']]['fx'], nav),
            'unrealized_pnl': f['sign'] * f['quantity'] * (f['price'] - f['entry']) * accounts[f['account']]['fx']}
            for f in futures]}


def _scenario_nav(prices, cash, spots, accounts, futures):
    required = {p['id'] for p in spots + futures}
    if set(prices) != required:
        raise PortfolioInputError('SCENARIO_REQUIRES_EVERY_POSITION_EXACTLY')
    nav = sum((c['amount'] * c['fx'] for c in cash), ZERO)
    nav += sum((s['quantity'] * dec(prices[s['id']], 'scenario.price') for s in spots), ZERO)
    nav += sum((a['wallet'] * a['fx'] for a in accounts.values()), ZERO)
    nav += sum((f['sign'] * f['quantity'] * (dec(prices[f['id']], 'scenario.price') - f['entry']) * accounts[f['account']]['fx'] for f in futures), ZERO)
    return nav


def _dca(existing, quantity, amount, entry):
    if existing is None:
        return {'state': 'NEW_POSITION', 'quantity': quantity, 'cost_basis': amount,
            'average_cost': entry, 'unrealized_pnl': ZERO, 'pnl_pct_of_cost': ZERO}
    old_qty, old_cost = existing['quantity'], existing['cost']
    qty = old_qty + quantity
    if old_cost is None:
        return {'state': 'UNKNOWN_COST_BASIS', 'quantity': qty, 'cost_basis': None,
            'average_cost': None, 'unrealized_pnl': None, 'pnl_pct_of_cost': None}
    cost = old_cost + amount
    # Classification is based on the old position at the proposed fill price.
    old_pnl = old_qty * entry - old_cost
    state = 'DCA_POSITIVE' if old_pnl > ZERO else 'DCA_NEGATIVE' if old_pnl < ZERO else 'AT_COST'
    return {'state': state, 'quantity': qty, 'cost_basis': cost,
        'average_cost': cost / qty if qty else None,
        'unrealized_pnl': qty * entry - cost, 'pnl_pct_of_cost': ratio(qty * entry - cost, cost)}


def _evidence(bundle, decision, as_of):
    if bundle is None:
        return {'status': 'NOT_RUN', 'agreement': 'UNKNOWN'}
    try:
        expected_market = 'SPOT' if decision['product'] == 'SPOT' else 'USD_M_FUTURES'
        p = bundle['plan']
        if (p['symbol'], p['venue'], p['market']) != (decision['symbol'], decision['venue'], expected_market):
            raise PortfolioInputError('EVIDENCE_SCOPE_MISMATCH')
        if bundle['profile'] != decision['profile']:
            raise PortfolioInputError('EVIDENCE_PROFILE_MISMATCH')
        cutoff = dec(bundle['cutoff_ms'], 'evidence.cutoff')
        age = Decimal(str(as_of.timestamp())) * 1000 - cutoff
        if age < ZERO or age > dec(bundle['max_age_ms'], 'evidence.max_age_ms'):
            raise PortfolioInputError('EVIDENCE_TIME_MISMATCH')
        w, s = bundle['agents']['wyckoff'], bundle['agents']['smc']
        sha = bundle['snapshot_sha256']
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise PortfolioInputError('INVALID_EVIDENCE_HASH')
        if any(a['snapshot_sha256'] != sha for a in (w, s)):
            raise PortfolioInputError('EVIDENCE_SNAPSHOT_MISMATCH')
        if any(a['status'] != 'ANALYZED' or a['evidence'].get('errors') for a in (w, s)):
            return {'status': 'UNKNOWN', 'agreement': 'UNKNOWN', 'snapshot_sha256': sha}
        if any(a['evidence']['symbol'] != decision['symbol'] for a in (w, s)):
            raise PortfolioInputError('EVIDENCE_SYMBOL_MISMATCH')
        wb, sb = w['evidence']['bias'], s['evidence']['bias']
        if wb not in ('BULLISH', 'BEARISH', 'NEUTRAL', 'UNKNOWN') or sb not in ('BULLISH', 'BEARISH', 'NEUTRAL', 'UNKNOWN'):
            raise PortfolioInputError('UNSUPPORTED_EVIDENCE_BIAS')
        agreement = 'CONFLICT' if {wb, sb} == {'BULLISH', 'BEARISH'} else 'ALIGNED_DIRECTION' if wb == sb and wb in ('BULLISH', 'BEARISH') else 'INCOMPLETE_OR_NEUTRAL'
        return {'status': 'SUPPLIED_NOT_AUTHENTICATED', 'agreement': agreement,
            'wyckoff_bias': wb, 'smc_bias': sb, 'snapshot_sha256': sha,
            'probability': None}
    except (KeyError, TypeError, PortfolioInputError) as exc:
        return {'status': 'REJECTED', 'agreement': 'UNKNOWN', 'reason': str(exc)}


def _run(data):
    if not isinstance(data, dict):
        raise PortfolioInputError('INPUT_OBJECT_REQUIRED')
    for key in ('portfolio', 'decision', 'cycle'):
        if not isinstance(data.get(key), dict):
            raise PortfolioInputError('OBJECT_REQUIRED:' + key)
    for key in ('cash', 'spot', 'futures_accounts', 'futures'):
        rows = data['portfolio'].get(key, [])
        if not isinstance(rows, list) or len(rows) > 1000 or any(not isinstance(r, dict) for r in rows):
            raise PortfolioInputError('INVALID_POSITION_LIST:' + key)
    if data['schema'] != 'portfolio-insider.input.v1':
        raise PortfolioInputError('UNSUPPORTED_SCHEMA')
    as_of = iso(data['as_of'], 'as_of')
    currency = text(data['reporting_currency'], 'reporting_currency')
    if data.get('data_source') != 'SELF_REPORTED':
        raise PortfolioInputError('UNSUPPORTED_INPUT_SOURCE')
    cash, spots, accounts, futures = _positions(data['portfolio'])
    cur = _current(cash, spots, accounts, futures)
    d, cycle = data['decision'], data['cycle']
    if d['product'] not in ('SPOT', 'LINEAR_FUTURES') or d['profile'] not in PROFILES:
        raise PortfolioInputError('UNSUPPORTED_PRODUCT_OR_PROFILE')
    asset, venue, symbol = text(d['asset'], 'decision.asset'), text(d['venue'], 'decision.venue'), text(d['symbol'], 'decision.symbol')
    horizon = text(d['holding_horizon'], 'holding_horizon')
    proposed = positive(d['proposed_amount'], 'proposed_amount')
    tolerance = percent(d['loss_tolerance_pct'], 'loss_tolerance_pct')
    budget = proposed * tolerance / HUNDRED  # Frozen before resizing.
    allocated = d.get('allocated_loss_budget')
    if allocated is not None:
        budget = min(budget, dec(allocated, 'allocated_loss_budget'))
    entry = positive(d['entry_price'], 'entry_price')
    stop = dec(d['stop_or_scenario_price'], 'stop_or_scenario_price')
    cycle_price = dec(d['cycle_price'], 'cycle_price')
    buffer_rate = percent(d.get('loss_buffer_pct', '0'), 'loss_buffer_pct') / HUNDRED
    anchor = positive(cycle['anchor_nav'], 'anchor_nav')
    anchor_id = text(cycle['anchor_id'], 'anchor_id')
    if iso(cycle['anchor_as_of'], 'anchor_as_of') > as_of:
        raise PortfolioInputError('ANCHOR_AFTER_AS_OF')
    if cycle.get('external_flows_reconciled') is not True:
        raise PortfolioInputError('EXTERNAL_FLOWS_NOT_RECONCILED')
    cycle_pct = percent(cycle['max_loss_pct'], 'cycle.max_loss_pct')
    floor = anchor * (ONE - cycle_pct / HUNDRED)
    baseline = _scenario_nav(cycle['prices'], cash, spots, accounts, futures)
    existing_id = d.get('position_id')
    existing = None
    sign, fx = ONE, ONE
    margin = 'NOT_APPLICABLE'
    reserve = dec(d.get('minimum_available_cash', '0'), 'minimum_available_cash')
    if d['product'] == 'SPOT':
        if d['intent'] not in ('BUY_SPOT', 'ADD_SPOT'):
            raise PortfolioInputError('UNSUPPORTED_SPOT_INTENT')
        if existing_id is not None:
            existing = next((p for p in spots if p['id'] == existing_id), None)
            if existing is None or (existing['asset'], existing['venue']) != (asset, venue):
                raise PortfolioInputError('POSITION_SCOPE_MISMATCH')
            if d.get('entry_mode', 'MARKET') not in ('MARKET', 'LIMIT'):
                raise PortfolioInputError('UNSUPPORTED_ENTRY_MODE')
            if d.get('entry_mode', 'MARKET') != 'LIMIT' and existing['price'] != entry:
                raise PortfolioInputError('ENTRY_NOT_CURRENT_REFERENCE')
            if positive(cycle['prices'][existing_id], 'cycle.selected_price') != cycle_price:
                raise PortfolioInputError('CYCLE_SCENARIO_INCONSISTENT')
        if d['intent'] == 'ADD_SPOT' and existing is None:
            raise PortfolioInputError('ADD_REQUIRES_EXISTING_POSITION')
        funding = next((c for c in cash if c['id'] == d['funding_id']), None)
        if funding is None:
            raise PortfolioInputError('MISSING_FUNDING_BUCKET')
        available = min(funding['available'] * funding['fx'], max(ZERO, cur['available_cash'] - reserve))
        funding_cap = available / (ONE + buffer_rate)
    else:
        if d['intent'] not in ('OPEN_FUTURES', 'ADD_FUTURES') or d['direction'] not in ('LONG', 'SHORT'):
            raise PortfolioInputError('UNSUPPORTED_FUTURES_INTENT')
        account = accounts.get(d['funding_id'])
        if account is None:
            raise PortfolioInputError('MISSING_FUTURES_ACCOUNT')
        fx = account['fx']
        sign = ONE if d['direction'] == 'LONG' else -ONE
        if existing_id is not None:
            existing = next((p for p in futures if p['id'] == existing_id), None)
            if existing is None or (existing['asset'], existing['venue'], existing['account'], existing['sign']) != (asset, venue, account['id'], sign):
                raise PortfolioInputError('POSITION_SCOPE_MISMATCH')
            if existing['price'] != entry or positive(cycle['prices'][existing_id], 'cycle.selected_price') != cycle_price:
                raise PortfolioInputError('FUTURES_REFERENCE_MISMATCH')
        if d['intent'] == 'ADD_FUTURES' and existing is None:
            raise PortfolioInputError('ADD_REQUIRES_EXISTING_POSITION')
        leverage = positive(d['leverage'], 'leverage')
        if leverage > Decimal(125):
            raise PortfolioInputError('UNSUPPORTED_LEVERAGE')
        if cur['futures_account_equity'][account['id']] <= ZERO:
            raise PortfolioInputError('NONPOSITIVE_FUTURES_EQUITY')
        funding_cap = None if account['available'] is None else account['available'] * fx / (ONE / leverage + buffer_rate)
        margin = 'UNKNOWN_NOT_A_LIQUIDATION_CHECK'
    distance = sign * (entry - stop)
    cycle_distance = sign * (entry - cycle_price)
    if distance <= ZERO or cycle_distance <= ZERO:
        raise PortfolioInputError('ADVERSE_SCENARIO_REQUIRED')
    per_decision_cap = budget * entry / (distance + entry * buffer_rate)
    headroom = baseline - floor
    cycle_cap = max(ZERO, headroom) * entry / (cycle_distance + entry * buffer_rate)
    cash_safe_pct = percent(d.get('minimum_cash_pct', '0'), 'minimum_cash_pct')
    cash_safe_rate = cash_safe_pct / HUNDRED
    cash_safe_cap = None
    if d['product'] == 'SPOT':
        # A purchase converts cash to spot; only the loss buffer reduces NAV.
        cash_safe_cap = max(ZERO, (cur['cash_value'] - cash_safe_rate * cur['nav']) /
            (ONE + buffer_rate - cash_safe_rate * buffer_rate))
    caps = {'decision': per_decision_cap, 'cycle': cycle_cap, 'requested': proposed}
    if cash_safe_cap is not None:
        caps['cash_safety'] = cash_safe_cap
    if funding_cap is not None:
        caps['funding_or_margin_estimate'] = funding_cap
    # Do not recommend new exposure when current NAV already breaches its anchor.
    if cur['nav'] < floor:
        caps['anchor_already_breached'] = ZERO
    max_amount = min(caps.values()).quantize(Decimal('.01'), rounding=ROUND_DOWN)
    def evaluate(amount):
        quantity = amount / (entry * fx)
        decision_loss = amount * distance / entry + amount * buffer_rate
        scenario_nav = baseline - amount * cycle_distance / entry - amount * buffer_rate
        gates = {'decision': within(decision_loss, budget),
            'cycle': within(max(ZERO, anchor - scenario_nav), anchor * cycle_pct / HUNDRED),
            'anchor_not_already_breached': cur['nav'] >= floor,
            'funding_or_margin_estimate': None if funding_cap is None else within(amount, funding_cap)}
        if d['product'] == 'SPOT':
            cash_after = cur['cash_value'] - amount * (ONE + buffer_rate)
            nav_after = cur['nav'] - amount * buffer_rate
            gates['cash_safety'] = nav_after > ZERO and cash_after >= cash_safe_rate * nav_after
        result = {'amount': amount, 'quantity': quantity, 'decision_loss': decision_loss,
            'decision_loss_pct_of_requested': ratio(decision_loss, proposed),
            'cycle_scenario_nav': scenario_nav,
            'cycle_drawdown_pct_from_anchor': ratio(max(ZERO, anchor - scenario_nav), anchor),
            'additional_decline_pct_from_current_nav': ratio(max(ZERO, cur['nav'] - scenario_nav), cur['nav']),
            'gates': gates, 'risk_limits_met': all(v is True for v in gates.values())}
        if d['product'] == 'SPOT':
            result['cash_after_purchase'] = cash_after
            result['nav_after_purchase'] = nav_after
            result['cash_ratio_after_purchase_pct'] = ratio(cash_after, nav_after)
            result['minimum_cash_pct'] = cash_safe_pct
        if d['product'] == 'SPOT':
            result['spot_after'] = _dca(existing, quantity, amount, entry)
            total_qty = result['spot_after']['quantity']
            old_cost = existing['cost'] if existing else ZERO
            new_cost = None if old_cost is None else old_cost + amount
            result['spot_after'].update({'scenario_value': total_qty * cycle_price,
                'cycle_unrealized_pnl': None if new_cost is None else total_qty * cycle_price - new_cost,
                'nav_pct': ratio(total_qty * entry, cur['nav']),
                'remaining_available_cash_before_fees': cur['available_cash'] - amount})
        else:
            result['estimated_initial_margin_quote'] = amount / fx / leverage
            old_qty = existing['quantity'] if existing else ZERO
            old_entry = existing['entry'] if existing else entry
            total_qty = old_qty + quantity
            avg = (old_qty * old_entry + quantity * entry) / total_qty if total_qty else None
            old_pnl = sign * old_qty * (entry - old_entry) * fx
            result['futures_after'] = {'quantity': total_qty, 'average_entry': avg,
                'unrealized_pnl': old_pnl, 'direction': d['direction'],
                'cycle_unrealized_pnl': None if avg is None else sign * total_qty * (cycle_price - avg) * fx,
                'margin_safety': margin, 'stop_status': 'HYPOTHETICAL_NOT_PLACED'}
        return result
    proposed_result, bounded_result = evaluate(proposed), evaluate(max_amount)
    evidence = _evidence(data.get('market_evidence'), d, as_of)
    findings = [{'code': 'SELF_REPORTED_SCOPE', 'severity': 'INFO'},
        {'code': 'TWO_RISK_BASES', 'severity': 'INFO', 'decision_base': proposed, 'cycle_base': anchor},
        {'code': 'SCENARIOS_NOT_PROBABILITIES', 'severity': 'INFO'}]
    if max_amount < proposed:
        findings.append({'code': 'REQUEST_EXCEEDS_BOUND', 'severity': 'REVIEW', 'requested': proposed, 'bounded': max_amount})
    if d['product'] == 'SPOT':
        state = proposed_result['spot_after']['state']
        findings.append({'code': state, 'severity': 'INFO'})
        if state == 'DCA_NEGATIVE': findings.append({'code': 'AVERAGING_DOWN_DOES_NOT_ERASE_LOSS', 'severity': 'REVIEW'})
        if state == 'DCA_POSITIVE': findings.append({'code': 'UNREALIZED_GAIN_CAN_BE_GIVEN_BACK', 'severity': 'REVIEW'})
    else:
        findings.append({'code': 'MARGIN_AND_LIQUIDATION_UNVERIFIED', 'severity': 'REVIEW'})
    if evidence['status'] != 'SUPPLIED_NOT_AUTHENTICATED' or evidence['agreement'] != 'ALIGNED_DIRECTION':
        findings.append({'code': 'MARKET_CONFIRMATION_INCOMPLETE_OR_CONFLICTING', 'severity': 'REVIEW'})
    if any(s['cost'] is None for s in spots):
        findings.append({'code': 'COST_BASIS_INCOMPLETE', 'severity': 'REVIEW'})
    exposures = {}
    for s in spots: exposures[s['asset']] = exposures.get(s['asset'], ZERO) + s['quantity'] * s['price']
    for f in futures: exposures[f['asset']] = exposures.get(f['asset'], ZERO) + f['sign'] * f['quantity'] * f['price'] * accounts[f['account']]['fx']
    return {'schema': 'portfolio-insider.report.v1', 'agent_id': VERSION,
        'status': 'ANALYTICAL_REVIEW_ONLY', 'as_of': data['as_of'], 'reporting_currency': currency,
        'input_sha256': fingerprint(data), 'data_source': 'SELF_REPORTED',
        'current': cur, 'net_directional_exposure_pct_nav': {a: ratio(v, cur['nav']) for a, v in exposures.items()},
        'risk_contract': {'cycle_anchor_id': anchor_id, 'cycle_anchor_as_of': cycle['anchor_as_of'],
            'cycle_anchor_nav': anchor, 'cycle_max_loss_pct': cycle_pct, 'cycle_nav_floor': floor,
            'current_nav_drawdown_pct_from_anchor': ratio(max(ZERO, anchor - cur['nav']), anchor),
            'baseline_cycle_scenario_nav': baseline, 'cycle_scenario_headroom': headroom,
            'decision_requested_amount': proposed, 'decision_loss_tolerance_pct': tolerance,
            'decision_loss_budget_frozen': budget, 'loss_buffer_pct': buffer_rate * HUNDRED},
        'sizing': {'caps': caps, 'bounded_amount': max_amount, 'binding_limits': [k for k, v in caps.items() if v == min(caps.values())]},
        'hold_unchanged': {'cycle_scenario_nav': baseline}, 'requested': proposed_result,
        'bounded': bounded_result, 'market_evidence': evidence,
        'market_request': {'asset': asset, 'symbol': symbol, 'venue': venue,
            'product': d['product'], 'profile': d['profile'], 'holding_horizon': horizon,
            'requested_timeframes': PROFILES[d['profile']], 'status': 'PROPOSED_NOT_FETCHED'},
        'findings': findings,
        'tapeout': {'status': 'NOT_REQUESTED', 'circuit_id': None,
            'candidate_checks': ['decision_loss <= frozen_budget', 'cycle_nav >= fixed_nav_floor', 'cash_after_purchase >= minimum_cash_pct / 100 * nav_after_purchase']},
        'limitations': ['User-supplied snapshot; not full ledger reconciliation.',
            'All other positions require explicit cycle prices; cash FX rates held fixed in scenarios.',
            'Cycle anchor must already be adjusted for external flows; no automatic reset.',
            'Risk bounds apply to supplied scenarios only, not guaranteed losses.',
            'Loss buffer is a stress allowance, not booked execution fees.',
            'Futures mark-to-market scenarios ignore liquidation, funding and venue margin rules.',
            'Net directional exposure is not a correlation model or hedge guarantee.',
            'No source authentication, LLM probability, order, account connection or circuit execution.']}


class PortfolioInsiderAgent:
    agent_id = VERSION

    def run(self, data):
        with localcontext() as ctx:
            ctx.prec = 50
            try:
                result = _run(deepcopy(data))
                return serialize(result)
            except (PortfolioInputError, KeyError, TypeError, InvalidOperation, ValueError) as exc:
                return {'schema': 'portfolio-insider.report.v1', 'agent_id': VERSION,
                    'status': 'NEEDS_DATA_OR_UNSUPPORTED', 'errors': [str(exc)],
                    'tapeout': {'status': 'NOT_REQUESTED', 'circuit_id': None}}
