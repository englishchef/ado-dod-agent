"""Tests for collect-raw API endpoint behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from app.api.main import app
from app.models.raw import (
    CollectionStatus,
    CollectorStatus,
    RawArtifactPaths,
    RawCollectionResult,
    RawCollectionSummary,
)
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def _result(status: str) -> RawCollectionResult:
    return RawCollectionResult(
        collection_run_id="dod-raw-20260101T000000Z-42",
        build_id=42,
        status=cast(CollectionStatus, status),
        collected_at=datetime.now(UTC),
        summary=RawCollectionSummary(),
        artifact_paths=RawArtifactPaths(raw_bundle="data/raw/42/raw_bundle.json"),
        collector_statuses=[CollectorStatus(name="run_context", status="completed")],
        errors=[],
    )


def test_collect_raw_endpoint_returns_result(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should return collection result for completed/partial runs."""

    from app.api.routes import runs as runs_route

    async def fake_collect_raw_metadata(_: Any) -> RawCollectionResult:
        return _result("partial")

    monkeypatch.setattr(runs_route, "collect_raw_metadata", fake_collect_raw_metadata)

    client = TestClient(app)
    response = client.post(
        "/api/v1/runs/collect-raw",
        json={
            "organization": "org",
            "project": "proj",
            "build_id": 42,
            "mode": "local",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "partial"


def test_collect_raw_endpoint_maps_failed_to_502(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should return 502 when mandatory build retrieval failed."""

    from app.api.routes import runs as runs_route

    async def fake_collect_raw_metadata(_: Any) -> RawCollectionResult:
        return _result("failed")

    monkeypatch.setattr(runs_route, "collect_raw_metadata", fake_collect_raw_metadata)

    client = TestClient(app)
    response = client.post(
        "/api/v1/runs/collect-raw",
        json={
            "organization": "org",
            "project": "proj",
            "build_id": 42,
            "mode": "local",
        },
    )
    assert response.status_code == 502
