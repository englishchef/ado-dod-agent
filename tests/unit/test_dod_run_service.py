"""Tests for Phase 7A orchestration service."""

from __future__ import annotations

from backend.app.services.orchestration import dod_run_service
from pytest import MonkeyPatch


def test_run_dod_agent_returns_run_summary(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        dod_run_service,
        "run_dod_workflow",
        lambda _: {
            "run_summary": {
                "schema_version": "1.0",
                "run_id": "dod-run-20260527T010203Z-1",
                "build_id": 1,
                "organization": "org",
                "project": "proj",
                "status": "completed",
                "started_at": "2026-05-27T00:00:00+00:00",
                "completed_at": "2026-05-27T00:01:00+00:00",
                "service_now_payload": None,
                "confidence": {"overall": 0.8},
                "artifact_paths": {"run_summary": "summary.json"},
                "warnings": [],
                "errors": [],
            }
        },
    )

    summary = dod_run_service.run_dod_agent({"build_id": 1})

    assert summary.status == "completed"
    assert summary.confidence == {"overall": 0.8}
