"""Tests for the LangGraph deployment entrypoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.app.graphs import dod_deployment_graph
from backend.app.models.run_summary import DodRunSummary, RunIssue
from pytest import MonkeyPatch


def test_make_graph_dod_imports_and_compiles() -> None:
    graph = dod_deployment_graph.make_graph_dod()

    assert graph is not None


def test_dod_graph_invokes_orchestration_service(monkeypatch: MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run_dod_agent(input_data: dict[str, Any]) -> DodRunSummary:
        calls.append(input_data)
        return DodRunSummary(
            run_id="dod-run-123",
            build_id=input_data["build_id"],
            organization=input_data["organization"],
            project=input_data["project"],
            status="completed_with_warnings",
            started_at=datetime(2026, 5, 27, tzinfo=UTC),
            completed_at=datetime(2026, 5, 27, 0, 1, tzinfo=UTC),
            service_now_payload={"change_description": "Change"},
            confidence={"overall": 0.82},
            artifact_paths={"run_summary": "data/output/123/run_summary.json"},
            warnings=[
                RunIssue(
                    severity="warning",
                    code="review",
                    message="Review recommended.",
                    phase="validation",
                )
            ],
            errors=[],
        )

    monkeypatch.setattr(dod_deployment_graph, "run_dod_agent", fake_run_dod_agent)

    graph = dod_deployment_graph.make_graph_dod()
    result = graph.invoke(
        {
            "organization": "ado-org",
            "project": "ado-project",
            "build_id": 123,
            "mode": "pipeline",
            "correlation_id": "test-correlation",
        }
    )

    assert calls == [
        {
            "organization": "ado-org",
            "project": "ado-project",
            "build_id": 123,
            "mode": "pipeline",
            "correlation_id": "test-correlation",
            "requested_by": None,
            "source": None,
            "metadata": {},
        }
    ]
    assert result["run_id"] == "dod-run-123"
    assert result["status"] == "completed_with_warnings"
    assert result["build_id"] == 123
    assert result["service_now_payload"] == {"change_description": "Change"}
    assert result["confidence"] == {"overall": 0.82}
    assert result["artifact_paths"] == {"run_summary": "data/output/123/run_summary.json"}
    assert result["warnings"][0]["code"] == "review"
    assert result["errors"] == []
