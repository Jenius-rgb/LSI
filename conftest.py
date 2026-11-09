"""Make the project packages importable from pytest without installing them."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT, ROOT / "sw", ROOT / "tools"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
