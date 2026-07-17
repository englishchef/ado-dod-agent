"""Smoke-check the LangGraph DoD deployment entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    from backend.app.graphs.dod_deployment_graph import make_graph_dod
    from backend.app.graphs.dod_deployment_state import normalize_dod_input
    from backend.app.utils.state_serialization import validate_graph_state
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.graphs.dod_deployment_graph import make_graph_dod
    from backend.app.graphs.dod_deployment_state import normalize_dod_input
    from backend.app.utils.state_serialization import validate_graph_state


def main() -> int:
    graph = make_graph_dod()
    nodes = sorted(getattr(graph, "nodes", {}).keys())
    if nodes:
        print(f"dod graph nodes: {', '.join(nodes)}")
    representative = normalize_dod_input(
        {
            "organization": "ado-org",
            "project": "ado-project",
            "build_id": 123456,
            "mode": "pipeline",
            "metadata": {"source": "offline-import-smoke"},
        }
    )
    diagnostics = validate_graph_state(
        representative,
        context="langgraph_import_smoke",
    )
    print(f"representative state size bytes: {diagnostics['state_size_bytes']}")
    print("dod graph compiled successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
