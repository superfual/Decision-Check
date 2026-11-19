"""Generate browser Python copies from canonical modules; never edit generated copies."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
for relative in ['portfolio_insider/brain.py','decision_logic.py']:
    source=root/'decision_check'/relative
    shutil.copyfile(source,root/'site/market-runtime/decision_check'/relative)
shutil.copyfile(root/'decision_check/portfolio_insider/brain.py',root/'site/portfolio-brain/brain.py')
