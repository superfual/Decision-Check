"""python -m decision_check collect BTCUSDT --market SPOT --out report.json"""
import argparse
import json
import sys
from pathlib import Path
from .market import collect, canonical, DataError
from .reports import make_report, verify_report, store_report


def main():
    p = argparse.ArgumentParser(description='Read-only market evidence and deterministic replay')
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('collect')
    c.add_argument('symbol')
    c.add_argument('--market', choices=['SPOT', 'USD_M_FUTURES'], default='SPOT')
    c.add_argument('--out', required=True)
    c.add_argument('--db', default='decision-check.sqlite3')
    v = sub.add_parser('verify')
    v.add_argument('report')
    args = p.parse_args()
    try:
        if args.command == 'collect':
            report = make_report(collect(args.symbol, args.market))
            report_id = store_report(args.db, report)
            Path(args.out).write_text(canonical(report) + '\n', encoding='utf-8')
            print(canonical({'status': 'RECORDED', 'report_id': report_id, 'kind': report['snapshot']['kind'], 'out': args.out}))
        else:
            report = json.loads(Path(args.report).read_text(encoding='utf-8'))
            verify_report(report)
            print('REPLAY_MATCH: snapshot integrity and deterministic analysis match; source authenticity not established.')
    except (DataError, ValueError, TypeError, KeyError, OSError) as exc:
        print(canonical({'status': 'DATA_UNAVAILABLE_OR_INVALID', 'detail': str(exc)}), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
