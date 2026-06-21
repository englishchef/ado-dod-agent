"""Deprecated wrapper for local Cosmos artifact smoke testing."""

from __future__ import annotations

import sys
from pathlib import Path

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from scripts.smoke_cosmos import main

    raise SystemExit(main(["--local", *sys.argv[1:]]))
