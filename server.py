import os
import runpy
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent / "sociomatic" / "sociomatic" / "biblioteca_python"

os.chdir(APP_DIR)
sys.path.insert(0, str(APP_DIR))
runpy.run_path(str(APP_DIR / "server.py"), run_name="__main__")
