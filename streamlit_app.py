from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
APPS_DIR = ROOT / "apps"

for candidate in (ROOT, APPS_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

runpy.run_path(str(APPS_DIR / "acceptance_app.py"), run_name="__main__")