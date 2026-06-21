"""Smoke-test the configured Cosmos artifact store."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

try:
    from backend.app.services.orchestration.dod_run_service import run_dod_agent
    from backend.app.services.storage.storage_factory import get_storage_store
    from backend.app.utils.config import Settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.services.orchestration.dod_run_service import run_dod_agent
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test Cosmos artifact storage.")
    parser.add_argument("--local", action="store_true", help="Load .env.local for emulator use.")
    parser.add_argument("--full-run", action="store_true")
    parser.add_argument("--build-id", type=int, default=None)
    return parser


def _settings(local: bool) -> Settings:
    if local:
        load_env_local()
    return Settings(DOD_STORAGE_BACKEND="cosmos")


def _missing_full_run_config(settings: Settings) -> list[str]:
    missing: list[str] = []
    for name in (
        "ADO_ORGANIZATION",
        "ADO_PROJECT",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
    ):
        if not getattr(settings, name):
            missing.append(name)
    return missing


def _run_artifact_smoke(settings: Settings) -> int:
    run_id = f"cosmos-smoke-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    artifact_type = "smoke_test"
    store = get_storage_store(settings, run_id=run_id)
    store.save_artifact(
        run_id=run_id,
        build_id=0,
        artifact_type=artifact_type,
        content={"status": "ok", "source": "smoke_cosmos"},
    )
    loaded = store.load_artifact(run_id, artifact_type)
    artifact_names = store.list_artifacts(run_id)
    if loaded.get("status") != "ok" or artifact_type not in artifact_names:
        print("Error: Cosmos smoke test failed to round-trip the test artifact.")
        return 2
    delete = getattr(store, "delete_artifact", None)
    if callable(delete):
        delete(run_id, artifact_type)
    print("Cosmos artifact store smoke test passed")
    return 0


def _run_full_smoke(settings: Settings, build_id: int | None) -> int:
    if build_id is None:
        print("Error: --build-id is required when --full-run is specified.")
        return 2
    missing = _missing_full_run_config(settings)
    if missing:
        print(
            "Skipping full Cosmos DoD run smoke test; missing runtime config: "
            + ", ".join(sorted(missing))
        )
        return 0
    summary = run_dod_agent(
        {
            "organization": settings.ADO_ORGANIZATION,
            "project": settings.ADO_PROJECT,
            "build_id": build_id,
            "mode": "local",
            "source": "smoke_cosmos",
        }
    )
    store = get_storage_store(settings, run_id=summary.run_id)
    _ = store.load_run_summary(summary.run_id)
    print(
        "Cosmos full DoD run smoke test completed "
        f"run_id={summary.run_id} build_id={summary.build_id} status={summary.status}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = _settings(args.local)
    try:
        if args.full_run:
            return _run_full_smoke(settings, args.build_id)
        return _run_artifact_smoke(settings)
    except ModuleNotFoundError as exc:
        if exc.name != "azure.cosmos":
            raise
        print(
            "Error: azure-cosmos is not installed in this environment. "
            "Install project dependencies before running the smoke test."
        )
        return 2
    except Exception as exc:
        print(f"Error: Cosmos smoke test failed: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
