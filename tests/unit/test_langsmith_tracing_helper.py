"""Tests for the LangSmith tracing wrapper."""

from __future__ import annotations

from typing import Any

from backend.app.services.observability import langsmith_tracing


def test_tracing_disabled_is_noop(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setattr(langsmith_tracing, "_langsmith_client", lambda: object())

    submitted = langsmith_tracing.trace_event("dod test", {"run_id": "run-1"})

    assert submitted is False
    assert calls == []


def test_tracing_helper_failure_does_not_raise(monkeypatch: Any) -> None:
    class FailingClient:
        def create_run(self, **_: Any) -> None:
            raise RuntimeError("remote unavailable")

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setattr(langsmith_tracing, "_langsmith_client", lambda: FailingClient())

    assert langsmith_tracing.trace_event("dod test", {"run_id": "run-1"}) is False


def test_metadata_only_mode_excludes_full_generated_payloads(monkeypatch: Any) -> None:
    captured: list[dict[str, Any]] = []

    class FakeClient:
        def create_run(self, **kwargs: Any) -> None:
            captured.append(kwargs)

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("DOD_TRACE_MODE", "metadata_only")
    monkeypatch.setattr(langsmith_tracing, "_langsmith_client", lambda: FakeClient())

    langsmith_tracing.trace_dod_run(
        input_data={"organization": "org", "project": "proj", "build_id": 123},
        result={
            "run_id": "run-1",
            "build_id": 123,
            "status": "completed",
            "service_now_payload": {"change_description": "full generated field"},
        },
        timings={"duration_ms": 12},
        storage_backend="local_json",
    )

    metadata = captured[0]["metadata"]
    assert metadata["run_id"] == "run-1"
    assert metadata["duration_ms"] == 12
    assert "summary" not in metadata
    assert "full generated field" not in str(metadata)


def test_summary_mode_includes_only_safe_summary(monkeypatch: Any) -> None:
    captured: list[dict[str, Any]] = []

    class FakeClient:
        def create_run(self, **kwargs: Any) -> None:
            captured.append(kwargs)

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("DOD_TRACE_MODE", "summary")
    monkeypatch.setattr(langsmith_tracing, "_langsmith_client", lambda: FakeClient())

    langsmith_tracing.trace_dod_run(
        input_data={"organization": "org", "project": "proj", "build_id": 123},
        result={
            "run_id": "run-1",
            "build_id": 123,
            "status": "completed",
            "service_now_payload": {"change_description": "full generated field"},
            "confidence": {"overall": 0.9},
            "artifact_paths": {"run_summary": "summary.json"},
        },
        timings={"duration_ms": 12},
        storage_backend="local_json",
    )

    metadata = captured[0]["metadata"]
    assert metadata["summary"]["artifact_count"] == 1
    assert metadata["summary"]["final_confidence"] == 0.9
    assert "full generated field" not in str(metadata)
