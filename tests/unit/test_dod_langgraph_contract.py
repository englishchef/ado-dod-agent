"""Tests for the LangGraph DoD adapter contract behavior."""

from __future__ import annotations

import inspect
from typing import Any

from backend.app.graphs import dod_deployment_graph
from pytest import MonkeyPatch


def test_graph_accepts_structured_input_and_returns_contract_shape(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run_dod_agent(input_data: dict[str, Any]) -> dict[str, Any]:
        calls.append(input_data)
        return {
            "run_id": "dod-run-42",
            "build_id": input_data["build_id"],
            "status": "completed",
            "service_now_payload": {"change_description": "Change"},
            "confidence": {"overall": 0.9},
            "rule_evaluation": {
                "summary": {
                    "highest_severity": "warning",
                    "recommended_status": "completed_with_warnings",
                    "triggered_rule_count": 1,
                }
            },
            "artifact_paths": {"run_summary": "summary.json"},
            "warnings": [],
            "errors": [],
        }

    monkeypatch.setattr(dod_deployment_graph, "run_dod_agent", fake_run_dod_agent)

    result = dod_deployment_graph.make_graph_dod().invoke(
        {
            "organization": "ado-org",
            "project": "ado-project",
            "build_id": 42,
            "correlation_id": "corr-42",
            "metadata": {"source": "unit-test"},
        }
    )

    assert calls[0]["organization"] == "ado-org"
    assert calls[0]["project"] == "ado-project"
    assert calls[0]["build_id"] == 42
    assert calls[0]["mode"] == "pipeline"
    assert calls[0]["correlation_id"] == "corr-42"
    assert calls[0]["metadata"] == {"source": "unit-test"}
    assert result["run_id"] == "dod-run-42"
    assert result["build_id"] == 42
    assert result["status"] == "completed"
    assert result["artifact_paths"] == {"run_summary": "summary.json"}
    assert result["warnings"] == []
    assert result["errors"] == []
    assert result["rule_evaluation_summary"]["recommended_status"] == "completed_with_warnings"


def test_langgraph_adapter_does_not_call_cosmos_directly() -> None:
    source = inspect.getsource(dod_deployment_graph)

    assert "cosmos" not in source.lower()
    assert "get_storage_store" not in source
