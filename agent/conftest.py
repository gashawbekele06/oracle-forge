"""
Root conftest.py — makes pytest find utils/tests/ from /app/agent working dir.
Adds /app to sys.path so both `utils` and `agent` modules are importable.
"""
import sys
from pathlib import Path

# /app/agent → /app
APP_ROOT = Path(__file__).parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
