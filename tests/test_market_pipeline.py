import copy
import json
import sqlite3
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse
from decision_check.market import COUNTS, INTERVALS, DataError, collect, validate_bars, digest
from decision_check.reports import make_report, verify_report, store_report

CUTOFF = 1794873600000


def bars(interval, count):
    step = INTERVALS[interval]
    last = (CUTOFF // step - 1) * step
    return [[last - (count - 1 - i) * step, '100', '102', '98', str(100 + (i % 5) * .1), '1000', last - (count - 1 - i) * step + step - 1] for i in range(count)]


def snapshot():
    return {'schema': 'decision-check.snapshot.v1', 'venue': 'BINANCE', 'market': 'SPOT',
        'symbol': 'BTCUSDT', 'source': 'https://data-api.binance.vision/api/v3/klines',
        'kind': 'SYNTHETIC_TEST', 'cutoff_ms': CUTOFF,
        'bars': {i: bars(i, n) for i, n in COUNTS.items()}}


class PipelineTests(unittest.TestCase):
    def test_source_and_cutoff_binding(self):
        for market, host, prefix in [('SPOT', 'data-api.binance.vision', '/api/v3'), ('USD_M_FUTURES', 'fapi.binance.com', '/fapi/v1')]:
            seen = []
            def request(url):
                seen.append(url)
                u = urlparse(url)
                self.assertEqual(u.netloc, host)
                self.assertTrue(u.path.startswith(prefix))
                if u.path.endswith('/time'):
                    return {'serverTime': CUTOFF}
                q = parse_qs(u.query)
                self.assertEqual(int(q['endTime'][0]), CUTOFF)
                interval = q['interval'][0]
                return bars(interval, int(q['limit'][0]))
            s = collect('btcusdt', market, request)
            self.assertEqual(s['market'], market)
            self.assertEqual(len(seen), 5)
            self.assertEqual(len(s['bars']['1h']), 300)

    def test_open_candle_is_excluded(self):
        rows = bars('1h', 301)
        t = CUTOFF // 3600000 * 3600000
        rows.append([t, '100', '101', '99', '100', '0', t + 3599999])
        self.assertEqual(len(validate_bars(rows, '1h', 300, CUTOFF)), 300)

    def test_reject_gap_duplicate_nan_stale(self):
        for error in ('gap', 'duplicate', 'nan', 'stale'):
            rows = bars('1h', 300)
            if error == 'gap': rows.pop(150)
            if error == 'duplicate': rows[150] = rows[149]
            if error == 'nan': rows[150][4] = 'NaN'
            if error == 'stale': rows = bars('1h', 301)[:-1]
            with self.subTest(error=error), self.assertRaises(DataError):
                validate_bars(rows, '1h', 300, CUTOFF)

    def test_replay_is_deterministic(self):
        a = make_report(snapshot())
        b = make_report(copy.deepcopy(snapshot()))
        self.assertEqual(a, b)
        self.assertTrue(verify_report(json.loads(json.dumps(a))))

    def test_tampering_and_version_rejected(self):
        original = make_report(snapshot())
        for edit in ('price', 'analysis', 'version', 'source', 'tapeout'):
            r = copy.deepcopy(original)
            if edit == 'price': r['snapshot']['bars']['1h'][-1][4] = '101'
            if edit == 'analysis': r['analysis']['wyckoff']['bias'] = 'FAKE'
            if edit == 'version': r['upstream_revision'] = 'other'
            if edit == 'source': r['snapshot']['market'] = 'USD_M_FUTURES'
            if edit == 'tapeout': r['tapeout']['status'] = 'VERIFIED'
            with self.subTest(edit=edit), self.assertRaises(DataError): verify_report(r)

    def test_sqlite_persists_idempotently(self):
        r = make_report(snapshot())
        with tempfile.TemporaryDirectory() as tmp:
            path = tmp + '/evidence.db'
            first = store_report(path, r)
            self.assertEqual(first, store_report(path, r))
            with sqlite3.connect(path) as db:
                rows = db.execute('SELECT payload FROM reports').fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0][0]), r)

if __name__ == '__main__': unittest.main()
