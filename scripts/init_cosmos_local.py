"""Initialize the local-only Cosmos DB emulator database/container."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from backend.app.services.storage.cosmos_local_store import CosmosLocalStore
    from backend.app.utils.config import Settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.services.storage.cosmos_local_store import CosmosLocalStore
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


def main() -> int:
    load_env_local()
    settings = Settings(DOD_STORAGE_BACKEND="cosmos_local")
    try:
        CosmosLocalStore(settings).initialize()
    except ModuleNotFoundError as exc:
        if exc.name != "azure.cosmos":
            raise
        print(
            "Error: azure-cosmos is not installed in this environment. "
            "Install project dependencies, then rerun the init script."
        )
        return 2
    except Exception:
        print(
            "Error: local Cosmos emulator initialization failed. "
            "Verify the emulator is running, COSMOS_LOCAL_* settings are correct, "
            "and the emulator certificate is trusted."
        )
        return 2

    print(
        "local Cosmos initialized "
        f"database={settings.COSMOS_LOCAL_DATABASE} "
        f"container={settings.COSMOS_LOCAL_CONTAINER} "
        "partition_key=/run_id"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
