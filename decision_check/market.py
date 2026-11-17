"""Read-only Binance market data. Spot and USD-M are never interchanged."""
import hashlib
import json
import math
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

INTERVALS = {'1d': 86400000, '4h': 14400000, '1h': 3600000, '15m': 900000}
COUNTS = {'1d': 120, '4h': 240, '1h': 300, '15m': 300}
SOURCES = {
    'SPOT': ('https://data-api.binance.vision', '/api/v3'),
    'USD_M_FUTURES': ('https://fapi.binance.com', '/fapi/v1'),
}

class DataError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def read_json(url):
    try:
        with urlopen(Request(url, headers={'Accept': 'application/json', 'User-Agent': 'DecisionCheck/0.1'}), timeout=15) as response:
            payload = response.read(8_000_001)
            if len(payload) > 8_000_000:
                raise DataError('RESPONSE_TOO_LARGE')
            return json.loads(payload)
    except HTTPError as exc:
        raise DataError(f'SOURCE_HTTP_{exc.code}') from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise DataError('SOURCE_UNAVAILABLE_OR_INVALID') from exc


def validate_bars(rows, interval, count, cutoff):
    if not isinstance(rows, list) or len(rows) > 1000:
        raise DataError('INVALID_KLINES')
    delta = INTERVALS[interval]
    closed, previous = [], None
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            raise DataError('MALFORMED_CANDLE')
        try:
            if type(row[0]) is not int or type(row[6]) is not int:
                raise DataError('INVALID_TIMESTAMP_TYPE')
            opened, ended = row[0], row[6]
            values = list(map(float, row[1:6]))
        except (ValueError, TypeError, OverflowError) as exc:
            raise DataError('MALFORMED_OHLCV') from exc
        o, h, l, c, v = values
        if opened < 0 or opened % delta or ended != opened + delta - 1:
            raise DataError('INCORRECT_INTERVAL')
        if previous is not None and opened <= previous:
            raise DataError('UNORDERED_OR_DUPLICATE')
        previous = opened
        if not all(math.isfinite(n) for n in values) or min(o, h, l, c) <= 0 or v < 0 or h < max(o, l, c) or l > min(o, c):
            raise DataError('INVALID_OHLCV')
        if ended < cutoff:
            closed.append(row)
    selected = closed[-count:]
    if len(selected) != count:
        raise DataError('INSUFFICIENT_CLOSED_CANDLES')
    if any(int(b[0]) - int(a[0]) != delta for a, b in zip(selected, selected[1:])):
        raise DataError('GAP_IN_CANDLES')
    if int(selected[-1][0]) != (cutoff // delta - 1) * delta:
        raise DataError('STALE_LAST_CANDLE')
    return selected


def validate_snapshot(s):
    try:
        if s['schema'] != 'decision-check.snapshot.v1' or s['venue'] != 'BINANCE':
            raise DataError('UNSUPPORTED_SNAPSHOT')
        if s['market'] not in SOURCES or not re.fullmatch(r'[A-Z0-9]{2,24}USDT', s['symbol']):
            raise DataError('UNSUPPORTED_MARKET_OR_SYMBOL')
        if type(s['cutoff_ms']) is not int or s['cutoff_ms'] <= 0:
            raise DataError('INVALID_CUTOFF')
        base, prefix = SOURCES[s['market']]
        if s['source'] != base + prefix + '/klines':
            raise DataError('SOURCE_MARKET_MISMATCH')
        if s['kind'] not in ('OBSERVED', 'SYNTHETIC_TEST'):
            raise DataError('UNKNOWN_DATA_KIND')
        if set(s['bars']) != set(COUNTS):
            raise DataError('MISSING_TIMEFRAME')
        for interval, count in COUNTS.items():
            if len(s['bars'][interval]) != count:
                raise DataError('WRONG_CANDLE_COUNT')
            validate_bars(s['bars'][interval], interval, count, s['cutoff_ms'])
        canonical(s)
    except (KeyError, TypeError, OverflowError) as exc:
        raise DataError('MALFORMED_SNAPSHOT') from exc
    return s


def collect(symbol, market='SPOT', request=read_json):
    symbol = str(symbol).strip().upper()
    if not re.fullmatch(r'[A-Z0-9]{2,24}USDT', symbol) or market not in SOURCES:
        raise DataError('UNSUPPORTED_MARKET_OR_SYMBOL')
    base, prefix = SOURCES[market]
    clock = request(base + prefix + '/time')
    if not isinstance(clock, dict) or type(clock.get('serverTime')) is not int or clock['serverTime'] <= 0:
        raise DataError('INVALID_SOURCE_CLOCK')
    cutoff = clock['serverTime']
    bars = {}
    for interval, count in COUNTS.items():
        query = urlencode({'symbol': symbol, 'interval': interval, 'limit': count + 5, 'endTime': cutoff})
        rows = request(base + prefix + '/klines?' + query)
        bars[interval] = validate_bars(rows, interval, count, cutoff)
    return validate_snapshot({'schema': 'decision-check.snapshot.v1', 'venue': 'BINANCE',
        'market': market, 'symbol': symbol, 'source': base + prefix + '/klines',
        'kind': 'OBSERVED', 'cutoff_ms': cutoff, 'bars': bars})
