"""Offline, read-only JSON analysis. No exchange credentials are accepted."""
import argparse
import json
from pathlib import Path
from . import PortfolioInsiderAgent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding='utf-8'))
        report = PortfolioInsiderAgent().run(data)
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + '\n')
    output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.write_text(output, encoding='utf-8')
    else:
        print(output, end='')
    return 0 if report['status'] == 'ANALYTICAL_REVIEW_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
