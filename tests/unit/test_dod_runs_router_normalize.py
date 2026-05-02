"""Tests for normalize endpoint behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.api.main import app
from backend.app.models.canonical import (
    CanonicalDodDocument,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def _canonical_document(build_id: int) -> CanonicalDodDocument:
    return CanonicalDodDocument(
        build_id=build_id,
        organization="org",
        project="proj",
        generated_at=datetime.now(UTC),
        source_raw_bundle_path=f"data/raw/{build_id}/raw_bundle.json",
        run_context=RunContext(build_id=build_id, pipeline_name="Pipeline"),
        change_context=ChangeContext(),
        execution_context=ExecutionContext(),
        quality_context=QualityContext(),
        risk_context=RiskContext(),
        normalization_metadata=NormalizationMetadata(),
    )


def test_normalize_endpoint_returns_expected_summary(monkeypatch: MonkeyPatch) -> None:
    """Normalize endpoint should return safe summary with canonical path."""

    from backend.app.routers import dod_runs as runs_route

    class DummyStore:
        def __init__(self, _: Any) -> None:
            pass

        def load_raw_bundle(self, build_id: int) -> dict[str, Any]:
            return {
                "build_id": build_id,
                "organization": "org",
                "project": "proj",
                "status": "completed",
                "raw": {"build": {"id": build_id}},
            }

        def raw_path(self, build_id: int, filename: str) -> str:
            return f"data/raw/{build_id}/{filename}"

        def save_normalized_json(self, build_id: int, filename: str, payload: Any) -> str:
            _ = payload
            return f"data/normalized/{build_id}/{filename}"

    def fake_normalize_raw_bundle(
        raw_bundle: dict[str, Any],
        source_path: str | None = None,
    ) -> Any:
        _ = (raw_bundle, source_path)
        return _canonical_document(42)

    def fake_build_summary(document: Any, path: str) -> dict[str, Any]:
        _ = document
        return {
            "status": "completed",
            "message": "Canonical normalization completed.",
            "build_id": 42,
            "pipeline_name": "Pipeline",
            "source_branch": None,
            "source_version": None,
            "work_item_count": 0,
            "commit_count": 0,
            "pull_request_count": 0,
            "stage_count": 0,
            "job_count": 0,
            "task_count": 0,
            "artifact_count": 0,
            "test_run_count": 0,
            "failed_test_count": 0,
            "risk_flags": [],
            "warnings": [],
            "canonical_path": path,
        }

    monkeypatch.setattr(runs_route, "LocalJsonStore", DummyStore)
    monkeypatch.setattr(runs_route, "normalize_raw_bundle", fake_normalize_raw_bundle)
    monkeypatch.setattr(runs_route, "build_canonical_summary", fake_build_summary)

    client = TestClient(app)
    response = client.post("/api/v1/runs/normalize", json={"build_id": 42})
    assert response.status_code == 200
    payload = response.json()
    assert payload["build_id"] == 42
    assert payload["pipeline_name"] == "Pipeline"
    assert payload["canonical_path"].endswith("data/normalized/42/canonical.json")
