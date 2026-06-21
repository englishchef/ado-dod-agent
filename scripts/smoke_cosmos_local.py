"""Smoke-test local-only Cosmos DB emulator artifact persistence."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

try:
    from backend.app.services.storage.storage_factory import get_storage_store
    from backend.app.utils.config import Settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.services.storage.storage_factory import get_storage_store
    from backend.app.utils.config import Settings


def load_env_local(path: Path | None = None) -> None:
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
    run_id = f"local-cosmos-smoke-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    artifact_type = "smoke_test"
    try:
        store = get_storage_store(settings)
        store.save_artifact(
            run_id=run_id,
            build_id=0,
            artifact_type=artifact_type,
            content={"status": "ok", "source": "smoke_cosmos_local"},
        )
        loaded = store.load_artifact(run_id, artifact_type)
        artifact_names = store.list_artifacts(run_id)
        if loaded.get("status") != "ok" or artifact_type not in artifact_names:
            print("Error: local Cosmos smoke test failed to round-trip the test artifact.")
            return 2
        delete = getattr(store, "delete_artifact", None)
        if callable(delete):
            delete(run_id, artifact_type)
    except ModuleNotFoundError as exc:
        if exc.name != "azure.cosmos":
            raise
        print(
            "Error: azure-cosmos is not installed in this environment. "
            "Install project dependencies before running the smoke test."
        )
        return 2
    except Exception:
        print(
            "Error: local Cosmos smoke test could not reach or use the emulator. "
            "Verify the emulator is running, .env.local is configured, "
            "COSMOS_LOCAL_KEY is set, and TLS/certificate trust is configured."
        )
        return 2

    print("local Cosmos smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
