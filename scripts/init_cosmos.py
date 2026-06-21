"""Initialize the configured Cosmos artifact store database/container."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

try:
    from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore
    from backend.app.utils.config import Settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore
    from backend.app.utils.config import Settings


def load_env_local(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries from .env.local without printing secrets."""

    env_path = path or Path(".env.local")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize Cosmos artifact storage.")
    parser.add_argument("--local", action="store_true", help="Load .env.local for emulator use.")
    parser.add_argument("--database", default=None)
    parser.add_argument("--container", default=None)
    return parser


def _settings_from_args(args: argparse.Namespace) -> Settings:
    if args.local:
        load_env_local()
    overrides: dict[str, Any] = {"DOD_STORAGE_BACKEND": "cosmos"}
    if args.database:
        overrides["COSMOS_DATABASE"] = args.database
    if args.container:
        overrides["COSMOS_CONTAINER"] = args.container
    return Settings(**overrides)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = _settings_from_args(args)
    try:
        CosmosArtifactStore(settings).initialize()
    except ModuleNotFoundError as exc:
        if exc.name != "azure.cosmos":
            raise
        print(
            "Error: azure-cosmos is not installed in this environment. "
            "Install project dependencies, then rerun the init script."
        )
        return 2
    except Exception as exc:
        print(f"Error: Cosmos initialization failed: {type(exc).__name__}: {exc}")
        return 2

    print(
        "Cosmos artifact store initialized "
        f"database={settings.resolved_cosmos_database} "
        f"container={settings.resolved_cosmos_container} "
        "partition_key=/run_id"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
