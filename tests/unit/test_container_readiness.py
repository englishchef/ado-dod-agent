"""Tests for container readiness smoke checks."""

from __future__ import annotations

from scripts import smoke_container_readiness


def test_smoke_container_readiness_imports_graph_without_remote_calls() -> None:
    summary = smoke_container_readiness.run_container_readiness()

    assert summary["fastapi_app_imported"] is True
    assert summary["graph_name"] == "dod"
    assert "run_dod" in summary["graph_nodes"]
    assert summary["contracts_imported"] is True
    assert summary["storage_imported"] is True
    assert summary["observability_imported"] is True
