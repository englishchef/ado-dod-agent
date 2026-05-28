"""Tests for workflow ASCII renderer script."""

from __future__ import annotations

from scripts.render_workflow_ascii import GraphEdge, render_ascii


def test_render_ascii_uses_graph_edges() -> None:
    rendered = render_ascii(
        [
            GraphEdge("__start__", "validate_input"),
            GraphEdge("validate_input", "collect_raw_metadata", "continue", True),
            GraphEdge("validate_input", "persist_run_summary", "failed", True),
            GraphEdge("collect_raw_metadata", "persist_run_summary"),
            GraphEdge("persist_run_summary", "__end__"),
        ]
    )

    assert "route_after_validate_input" in rendered
    assert "validate_input -> collect_raw_metadata [continue] (conditional)" in rendered
    assert "persist_run_summary -> END (direct)" in rendered
