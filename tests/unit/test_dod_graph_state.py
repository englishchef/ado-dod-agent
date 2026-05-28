"""Tests for Phase 7A state and run summary models."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.graphs.nodes import validate_input_node
from backend.app.models.run_summary import DodRunSummary, RunIssue


def test_run_issue_serializes() -> None:
    issue = RunIssue(severity="warning", code="gap", message="Missing PR.", phase="evidence")

    payload = issue.model_dump(mode="json")

    assert payload == {
        "severity": "warning",
        "code": "gap",
        "message": "Missing PR.",
        "phase": "evidence",
    }


def test_dod_run_summary_serializes() -> None:
    summary = DodRunSummary(
        run_id="dod-run-20260527T010203Z-5",
        build_id=5,
        organization="org",
        project="proj",
        status="completed",
        started_at=datetime(2026, 5, 27, tzinfo=UTC),
        completed_at=datetime(2026, 5, 27, 0, 1, tzinfo=UTC),
        confidence={"overall": 0.8},
        artifact_paths={"run_summary": "data/output/5/run_summary.json"},
        warnings=[],
        errors=[],
    )

    payload = summary.model_dump(mode="json")

    assert payload["schema_version"] == "1.0"
    assert payload["started_at"].startswith("2026-05-27")
    assert payload["confidence"]["overall"] == 0.8


def test_validate_input_node_fails_when_build_id_missing() -> None:
    state = validate_input_node({"input": {"organization": "org", "project": "proj"}})

    assert state["status"] == "failed"
    assert state["build_id"] == 0
    assert state["errors"][0]["code"] == "invalid_build_id"


def test_validate_input_node_initializes_run_state() -> None:
    state = validate_input_node(
        {"input": {"organization": "org", "project": "proj", "build_id": 123}}
    )

    assert state["status"] == "started"
    assert state["run_id"].startswith("dod-run-")
    assert state["run_id"].endswith("-123")
    assert state["started_at"]
    assert state["artifact_paths"] == {}
