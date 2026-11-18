"""Run independent market brains, or combine with a Portfolio Insider input."""
import argparse,json
from pathlib import Path
from .profile_data import collect_profile
from .market_brains import run_market_brains
from .decision_logic import evaluate_three


def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--snapshot',type=Path)
    source.add_argument('--collect',metavar='SYMBOL')
    p.add_argument('--market',choices=['SPOT','USD_M_FUTURES'],default='SPOT')
    p.add_argument('--profile',choices=['CYCLE','SWING','INTRADAY'],default='SWING')
    p.add_argument('--portfolio',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    s=json.loads(a.snapshot.read_text()) if a.snapshot else collect_profile(a.collect,a.market,a.profile)
    report=evaluate_three(json.loads(a.portfolio.read_text()),s) if a.portfolio else run_market_brains(s)
    a.out.write_text(json.dumps({'snapshot':s,'report':report},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
