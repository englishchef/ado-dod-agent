"""Tests for LangGraph deployment config."""

from __future__ import annotations

from scripts.smoke_container_readiness import (
    graph_entrypoint,
    load_langgraph_config,
    resolve_graph_entrypoint,
)


def test_langgraph_json_contains_dod_graph() -> None:
    config = load_langgraph_config()

    assert graph_entrypoint(config, "dod") == (
        "backend/app/graphs/dod_deployment_graph.py:make_graph_dod"
    )


def test_langgraph_json_graph_entrypoint_resolves() -> None:
    config = load_langgraph_config()
    resolved = resolve_graph_entrypoint(graph_entrypoint(config, "dod"))

    assert callable(resolved)
    assert resolved.__name__ == "make_graph_dod"
