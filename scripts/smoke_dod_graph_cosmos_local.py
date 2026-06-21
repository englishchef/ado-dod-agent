"""Optionally run the DoD graph with local Cosmos emulator storage."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

try:
    from backend.app.graphs.dod_deployment_graph import make_graph_dod
    from backend.app.services.storage.storage_factory import get_storage_store
    from backend.app.utils.config import Settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.graphs.dod_deployment_graph import make_graph_dod
    from backend.app.services.storage.storage_factory import get_storage_store
    from backend.app.utils.config import Settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run DoD graph with local Cosmos storage.")
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--organization", default=None)
    parser.add_argument("--project", default=None)
    return parser


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


def _missing_runtime_config(
    settings: Settings,
    organization: str | None,
    project: str | None,
) -> list[str]:
    missing: list[str] = []
    if not organization:
        missing.append("ADO_ORGANIZATION")
    if not project:
        missing.append("ADO_PROJECT")
    for name in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
        "COSMOS_LOCAL_KEY",
    ):
        if not getattr(settings, name):
            missing.append(name)
    return missing


def main() -> int:
    args = _build_parser().parse_args()
    load_env_local()
    settings = Settings(DOD_STORAGE_BACKEND="cosmos_local")
    organization = args.organization or settings.ADO_ORGANIZATION
    project = args.project or settings.ADO_PROJECT
    missing = _missing_runtime_config(settings, organization, project)
    if missing:
        print(
            "Skipping DoD graph local Cosmos smoke test; missing runtime config: "
            + ", ".join(sorted(missing))
        )
        return 0

    try:
        graph = make_graph_dod()
        result: dict[str, Any] = graph.invoke(
            {
                "organization": organization,
                "project": project,
                "build_id": args.build_id,
                "mode": "local",
                "source": "smoke_dod_graph_cosmos_local",
            }
        )
        store = get_storage_store(settings)
        _ = store.load_run_summary(args.build_id)
    except ModuleNotFoundError as exc:
        if exc.name != "azure.cosmos":
            raise
        print(
            "Skipping DoD graph local Cosmos smoke test because azure-cosmos is not "
            "installed in this environment."
        )
        return 0
    except Exception:
        print(
            "Error: DoD graph local Cosmos smoke test failed. Verify ADO, LLM, "
            "and local Cosmos emulator settings before rerunning."
        )
        return 2

    print(
        "DoD graph local Cosmos smoke test completed "
        f"run_id={result.get('run_id') or 'n/a'} "
        f"build_id={result.get('build_id') or args.build_id} "
        f"status={result.get('status') or 'n/a'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
