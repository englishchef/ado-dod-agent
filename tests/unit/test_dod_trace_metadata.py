"""Tests for DoD run trace metadata at the orchestration boundary."""

from __future__ import annotations

from typing import Any

from backend.app.services.orchestration import dod_run_service
from backend.app.utils.config import Settings


def _final_state() -> dict[str, Any]:
    return {
        "run_summary": {
            "schema_version": "1.0",
            "run_id": "dod-run-1",
            "build_id": 123,
            "organization": "org",
            "project": "proj",
            "status": "completed",
            "started_at": "2026-06-22T00:00:00+00:00",
            "completed_at": "2026-06-22T00:00:01+00:00",
            "duration_ms": 1000,
            "service_now_payload": None,
            "confidence": {"overall": 0.8},
            "artifact_paths": {"run_summary": "summary.json"},
            "phase_durations_ms": {"input_normalization": 1},
            "warnings": [],
            "errors": [],
        },
        "phase_durations_ms": {"input_normalization": 1},
    }


def test_run_dod_agent_passes_safe_trace_metadata(monkeypatch: Any) -> None:
    captured: list[dict[str, Any]] = []

    def fake_trace_dod_run(**kwargs: Any) -> None:
        captured.append(kwargs)

    monkeypatch.setattr(dod_run_service, "run_dod_workflow", lambda _: _final_state())
    monkeypatch.setattr(dod_run_service, "trace_dod_run", fake_trace_dod_run)
    monkeypatch.setattr(
        dod_run_service,
        "get_settings",
        lambda: Settings(DOD_STORAGE_BACKEND="local_json"),
    )

    summary = dod_run_service.run_dod_agent(
        {
            "organization": "org",
            "project": "proj",
            "build_id": 123,
            "correlation_id": "corr-123",
        }
    )

    assert summary.run_id == "dod-run-1"
    assert captured[0]["input_data"]["correlation_id"] == "corr-123"
    assert captured[0]["result"]["run_id"] == "dod-run-1"
    assert captured[0]["timings"]["phase_durations_ms"] == {"input_normalization": 1}
    assert captured[0]["storage_backend"] == "local_json"


def test_run_dod_agent_ignores_tracing_helper_failure(monkeypatch: Any) -> None:
    monkeypatch.setattr(dod_run_service, "run_dod_workflow", lambda _: _final_state())
    monkeypatch.setattr(
        dod_run_service,
        "trace_dod_run",
        lambda **_: (_ for _ in ()).throw(RuntimeError("trace failed")),
    )

    summary = dod_run_service.run_dod_agent({"build_id": 123})

    assert summary.status == "completed"
