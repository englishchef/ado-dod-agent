"""Pytest path bootstrap for local executions.

Ensures repository-root imports like `backend.*` and `scripts.*` resolve
when pytest is launched from different shell entrypoints on Windows.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ["DOD_STORAGE_BACKEND"] = "local_json"
