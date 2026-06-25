"""Smoke-check container readiness for LangGraph-native DoD deployment."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

try:
    from backend.app.graphs.dod_deployment_graph import make_graph_dod
    from backend.app.models.dod_contracts import DoDRunInput, DoDRunOutput
    from backend.app.services.observability.langsmith_tracing import is_tracing_enabled
    from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore
    from backend.app.services.storage.storage_factory import get_storage_store
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.graphs.dod_deployment_graph import make_graph_dod
    from backend.app.models.dod_contracts import DoDRunInput, DoDRunOutput
    from backend.app.services.observability.langsmith_tracing import is_tracing_enabled
    from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore
    from backend.app.services.storage.storage_factory import get_storage_store

LANGGRAPH_CONFIG_PATH = Path("langgraph.json")
GRAPH_NAME = "dod"


def load_langgraph_config(path: Path = LANGGRAPH_CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the LangGraph config file shape."""

    if not path.exists():
        raise FileNotFoundError("langgraph.json was not found in the working directory.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("langgraph.json must be a JSON object.")
    return payload


def graph_entrypoint(config: dict[str, Any], graph_name: str = GRAPH_NAME) -> str:
    """Return the configured graph entrypoint for a graph name."""

    graphs = config.get("graphs")
    if not isinstance(graphs, dict) or graph_name not in graphs:
        raise ValueError(f"langgraph.json must register graph name {graph_name!r}.")
    entrypoint = graphs[graph_name]
    if not isinstance(entrypoint, str) or ":" not in entrypoint:
        raise ValueError(f"Graph {graph_name!r} entrypoint must use module.py:function format.")
    return entrypoint


def resolve_graph_entrypoint(entrypoint: str) -> Any:
    """Import a LangGraph entrypoint from a langgraph.json path string."""

    module_path, function_name = entrypoint.split(":", 1)
    if not module_path.endswith(".py"):
        raise ValueError("Graph entrypoint module path must end with .py.")
    module_name = module_path[:-3].replace("/", ".").replace("\\", ".")
    module = importlib.import_module(module_name)
    resolved = getattr(module, function_name, None)
    if not callable(resolved):
        raise ValueError(f"Graph entrypoint function {function_name!r} is not callable.")
    return resolved


def run_container_readiness() -> dict[str, Any]:
    """Run safe import/config checks and return a compact summary."""

    from backend.api.main import app

    config = load_langgraph_config()
    entrypoint = graph_entrypoint(config)
    resolved_entrypoint = resolve_graph_entrypoint(entrypoint)
    graph = make_graph_dod()
    nodes = sorted(getattr(graph, "nodes", {}).keys())
    if not nodes:
        raise ValueError("Compiled dod graph did not expose any nodes.")
    if resolved_entrypoint is not make_graph_dod:
        raise ValueError("langgraph.json dod entrypoint does not resolve to make_graph_dod.")

    _ = (DoDRunInput, DoDRunOutput, get_storage_store, CosmosArtifactStore, is_tracing_enabled)
    return {
        "fastapi_app_imported": app is not None,
        "graph_name": GRAPH_NAME,
        "graph_entrypoint": entrypoint,
        "graph_nodes": nodes,
        "contracts_imported": True,
        "storage_imported": True,
        "observability_imported": True,
    }


def main() -> int:
    try:
        summary = run_container_readiness()
    except Exception as exc:
        print(f"Error: container readiness check failed: {type(exc).__name__}: {exc}")
        return 2

    print("Container readiness smoke test passed")
    print(f"- graph_name: {summary['graph_name']}")
    print(f"- graph_entrypoint: {summary['graph_entrypoint']}")
    print(f"- graph_nodes: {', '.join(summary['graph_nodes'])}")
    print("- fastapi_app_imported: true")
    print("- contracts_imported: true")
    print("- storage_imported: true")
    print("- observability_imported: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
