"""Smoke-check the LangGraph DoD deployment entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    from backend.app.graphs.dod_deployment_graph import make_graph_dod
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.graphs.dod_deployment_graph import make_graph_dod


def main() -> int:
    graph = make_graph_dod()
    nodes = sorted(getattr(graph, "nodes", {}).keys())
    if nodes:
        print(f"dod graph nodes: {', '.join(nodes)}")
    print("dod graph compiled successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
