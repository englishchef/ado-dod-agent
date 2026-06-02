"""Tests for Phase 8 /api/v1/runs/generate endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.api.main import app
from backend.app.models.run_summary import DodRunSummary, RunIssue
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

SERVICE_NOW_FIELDS = {
    "change_description": "Change description text",
    "short_change_description": "Short change",
    "justification": "Justification text",
    "testing_performed": "Testing performed text",
    "implementation_plan": "Implementation plan text",
    "validation_plan": "Validation plan text",
    "backout_plan": "Backout plan text",
    "risk_impact_analysis": "Risk analysis text",
}


def _summary(status: str, payload: dict[str, Any] | None = None) -> DodRunSummary:
    return DodRunSummary(
        run_id="dod-run-20260601T010203Z-123",
        build_id=123,
        organization="org",
        project="proj",
        status=status,
        started_at=datetime(2026, 6, 1, tzinfo=UTC),
        completed_at=datetime(2026, 6, 1, 0, 1, tzinfo=UTC),
        service_now_payload=payload,
        confidence={"overall": 0.82},
        artifact_paths={"run_summary": "summary.json", "service_now_payload": "payload.json"},
        warnings=[RunIssue(severity="warning", code="gap", message="Missing test evidence.")],
        errors=[],
    )


def _request(correlation_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization": "org",
        "project": "proj",
        "build_id": 123,
        "mode": "pipeline",
    }
    if correlation_id:
        payload["correlation_id"] = correlation_id
    return payload


def test_generate_endpoint_calls_run_dod_agent(monkeypatch: MonkeyPatch) -> None:
    from backend.app.routers import dod_runs as runs_route

    captured: dict[str, Any] = {}

    def fake_run_dod_agent(input_data: dict[str, Any]) -> DodRunSummary:
        captured.update(input_data)
        return _summary("completed", SERVICE_NOW_FIELDS)

    monkeypatch.setattr(runs_route, "run_dod_agent", fake_run_dod_agent)
    response = TestClient(app).post("/api/v1/runs/generate", json=_request())

    assert response.status_code == 200
    assert captured["mode"] == "pipeline"
    assert response.json()["service_now_payload"] == SERVICE_NOW_FIELDS


def test_generate_endpoint_completed_returns_200(monkeypatch: MonkeyPatch) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(
        runs_route,
        "run_dod_agent",
        lambda _: _summary("completed", SERVICE_NOW_FIELDS),
    )

    response = TestClient(app).post("/api/v1/runs/generate", json=_request())

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_generate_endpoint_completed_with_warnings_returns_200(
    monkeypatch: MonkeyPatch,
) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(
        runs_route,
        "run_dod_agent",
        lambda _: _summary("completed_with_warnings", SERVICE_NOW_FIELDS),
    )

    response = TestClient(app).post("/api/v1/runs/generate", json=_request())

    assert response.status_code == 200
    assert response.json()["status"] == "completed_with_warnings"


def test_generate_endpoint_needs_review_returns_200(monkeypatch: MonkeyPatch) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(
        runs_route,
        "run_dod_agent",
        lambda _: _summary("needs_review", SERVICE_NOW_FIELDS),
    )

    response = TestClient(app).post("/api/v1/runs/generate", json=_request())

    assert response.status_code == 200
    assert response.json()["status"] == "needs_review"


def test_generate_endpoint_failed_without_payload_returns_500(
    monkeypatch: MonkeyPatch,
) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(runs_route, "run_dod_agent", lambda _: _summary("failed", None))

    response = TestClient(app).post("/api/v1/runs/generate", json=_request())

    assert response.status_code == 500
    assert response.json()["code"] == "orchestration_failed"


def test_generate_endpoint_response_includes_payload_confidence_and_artifacts(
    monkeypatch: MonkeyPatch,
) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(
        runs_route,
        "run_dod_agent",
        lambda _: _summary("completed", SERVICE_NOW_FIELDS),
    )

    payload = TestClient(app).post("/api/v1/runs/generate", json=_request()).json()

    assert set(payload["service_now_payload"]) == set(SERVICE_NOW_FIELDS)
    assert payload["confidence"]["overall"] == 0.82
    assert payload["artifact_paths"]["run_summary"] == "summary.json"


def test_generate_endpoint_accepts_x_correlation_id_header(monkeypatch: MonkeyPatch) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(
        runs_route,
        "run_dod_agent",
        lambda _: _summary("completed", SERVICE_NOW_FIELDS),
    )

    response = TestClient(app).post(
        "/api/v1/runs/generate",
        json=_request(),
        headers={"X-Correlation-ID": "header-corr"},
    )

    assert response.json()["correlation_id"] == "header-corr"


def test_generate_endpoint_body_correlation_id_overrides_header(
    monkeypatch: MonkeyPatch,
) -> None:
    from backend.app.routers import dod_runs as runs_route

    captured: dict[str, Any] = {}

    def fake_run_dod_agent(input_data: dict[str, Any]) -> DodRunSummary:
        captured.update(input_data)
        return _summary("completed", SERVICE_NOW_FIELDS)

    monkeypatch.setattr(runs_route, "run_dod_agent", fake_run_dod_agent)
    response = TestClient(app).post(
        "/api/v1/runs/generate",
        json=_request("body-corr"),
        headers={"X-Correlation-ID": "header-corr"},
    )

    assert response.json()["correlation_id"] == "body-corr"
    assert captured["correlation_id"] == "body-corr"


def test_generate_endpoint_hides_stack_trace_on_orchestration_failure(
    monkeypatch: MonkeyPatch,
) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(
        runs_route,
        "run_dod_agent",
        lambda _: (_ for _ in ()).throw(RuntimeError("token Authorization secret traceback")),
    )

    response = TestClient(app).post("/api/v1/runs/generate", json=_request())
    body = str(response.json()).lower()

    assert response.status_code == 500
    assert "traceback" not in body
    assert "authorization" not in body
    assert "token" not in body
