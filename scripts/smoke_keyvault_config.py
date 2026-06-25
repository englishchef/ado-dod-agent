"""Live smoke-check for fetching the DoD agent JSON config secret."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

try:
    from backend.app.core.enterprise_config import load_agent_config_from_key_vault
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.core.enterprise_config import load_agent_config_from_key_vault


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate live Key Vault access to the DoD agent config secret."
    )
    parser.add_argument("--print-keys", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        config = load_agent_config_from_key_vault(strict=True)
    except Exception as exc:
        print(f"Error: Key Vault config smoke failed: {type(exc).__name__}: {exc}")
        return 2

    print("Key Vault config smoke passed")
    print("- secret_found: true")
    print(f"- top_level_key_count: {len(config)}")
    if args.print_keys:
        print("- key_names: " + ", ".join(sorted(config.keys())))
    print("Secret values are intentionally not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
