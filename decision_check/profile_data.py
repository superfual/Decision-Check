"""Profile-specific public OHLCV snapshots. No account data or product fallback."""
from datetime import datetime, timezone
from urllib.parse import urlencode
import math
import re
from .market import DataError, SOURCES, canonical, digest, read_json

PROFILES = {
    'CYCLE': {'counts': {'1M': 60, '1w': 120, '1d': 300}, 'context': '1M', 'wyckoff': '1w', 'smc': '1d'},
    'SWING': {'counts': {'1d': 120, '4h': 240, '1h': 300}, 'context': '1d', 'wyckoff': '4h', 'smc': '1h'},
    'INTRADAY': {'counts': {'4h': 120, '1h': 300, '15m': 300}, 'context': '4h', 'wyckoff': '1h', 'smc': '15m'},
}
DELTAS = {'1w': 604800000, '1d': 86400000, '4h': 14400000, '1h': 3600000, '15m': 900000}


def next_open(opened, interval):
    if interval != '1M':
        delta = DELTAS[interval]
        offset = 345600000 if interval == '1w' else 0  # Monday UTC
        if (opened - offset) % delta:
            raise DataError('INCORRECT_INTERVAL_ALIGNMENT')
        return opened + delta
    d = datetime.fromtimestamp(opened / 1000, timezone.utc)
    if d.day != 1 or any((d.hour, d.minute, d.second, d.microsecond)):
        raise DataError('INCORRECT_MONTH_ALIGNMENT')
    return int(datetime(d.year + (d.month == 12), d.month % 12 + 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def bars_at_cutoff(rows, interval, count, cutoff):
    if not isinstance(rows, list) or len(rows) > 1000:
        raise DataError('INVALID_KLINES')
    closed, prev = [], None
    for row in rows:
        if not isinstance(row, list) or len(row) < 7 or type(row[0]) is not int or type(row[6]) is not int:
            raise DataError('MALFORMED_CANDLE')
        opened, ended = row[0], row[6]
        if opened < 0 or ended != next_open(opened, interval) - 1:
            raise DataError('INCORRECT_INTERVAL')
        if prev is not None and opened <= prev:
            raise DataError('UNORDERED_OR_DUPLICATE')
        prev = opened
        if any(isinstance(x, bool) for x in row[1:6]):
            raise DataError('INVALID_OHLCV')
        try:
            o, h, l, c, v = map(float, row[1:6])
        except (TypeError, ValueError, OverflowError) as exc:
            raise DataError('INVALID_OHLCV') from exc
        if not all(math.isfinite(x) for x in (o,h,l,c,v)) or min(o,h,l,c) <= 0 or v < 0 or h < max(o,l,c) or l > min(o,c):
            raise DataError('INVALID_OHLCV')
        if ended < cutoff:
            closed.append(row)
    selected = closed[-count:]
    if len(selected) != count:
        raise DataError('INSUFFICIENT_CLOSED_CANDLES')
    if any(next_open(a[0], interval) != b[0] for a,b in zip(selected, selected[1:])):
        raise DataError('GAP_IN_CANDLES')
    # Last completed candle must immediately precede the candle containing cutoff.
    if not (selected[-1][6] + 1 <= cutoff < next_open(selected[-1][6] + 1, interval)):
        raise DataError('STALE_LAST_CANDLE')
    return selected


def validate_profile_snapshot(s):
    try:
        if s['schema'] != 'decision-check.profile-snapshot.v1' or s['venue'] != 'BINANCE':
            raise DataError('UNSUPPORTED_SNAPSHOT')
        if s['market'] not in SOURCES or not re.fullmatch(r'[A-Z0-9]{2,24}USDT', s['symbol']):
            raise DataError('UNSUPPORTED_MARKET_OR_SYMBOL')
        if s['profile'] not in PROFILES or type(s['cutoff_ms']) is not int or s['cutoff_ms'] <= 0:
            raise DataError('INVALID_PROFILE_OR_CUTOFF')
        base,prefix = SOURCES[s['market']]
        if s['source'] != base + prefix + '/klines' or s['kind'] not in ('OBSERVED','SYNTHETIC_TEST'):
            raise DataError('INVALID_PROVENANCE')
        counts = PROFILES[s['profile']]['counts']
        if set(s['bars']) != set(counts):
            raise DataError('PROFILE_TIMEFRAMES_MISMATCH')
        for interval,count in counts.items():
            if len(s['bars'][interval]) != count:
                raise DataError('WRONG_CANDLE_COUNT')
            bars_at_cutoff(s['bars'][interval], interval, count, s['cutoff_ms'])
        canonical(s)
    except (KeyError, TypeError, ValueError, OverflowError, OSError) as exc:
        raise DataError(str(exc)) from exc
    return s


def collect_profile(symbol, market='SPOT', profile='SWING', request=read_json):
    if market not in SOURCES or profile not in PROFILES or not re.fullmatch(r'[A-Z0-9]{2,24}USDT', symbol):
        raise DataError('UNSUPPORTED_SCOPE')
    base,prefix = SOURCES[market]
    cutoff = request(base+prefix+'/time')['serverTime']
    if type(cutoff) is not int or cutoff <= 0: raise DataError('INVALID_SOURCE_CLOCK')
    bars={}
    for interval,count in PROFILES[profile]['counts'].items():
        rows=request(base+prefix+'/klines?'+urlencode({'symbol':symbol,'interval':interval,'limit':count+5,'endTime':cutoff}))
        bars[interval]=bars_at_cutoff(rows,interval,count,cutoff)
    return validate_profile_snapshot({'schema':'decision-check.profile-snapshot.v1','venue':'BINANCE',
        'symbol':symbol,'market':market,'profile':profile,'kind':'OBSERVED','cutoff_ms':cutoff,
        'source':base+prefix+'/klines','bars':bars})
