from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "apps" / "acceptance_app.py"), run_name="__main__")
