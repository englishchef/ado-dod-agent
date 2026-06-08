"""Tests for Phase 9 read-only rule evaluation endpoint."""

from __future__ import annotations

from pathlib import Path

from backend.api.main import app
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import Settings
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def _patch_settings(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    from backend.app.routers import dod_runs as runs_route

    monkeypatch.setattr(runs_route, "get_settings", lambda: Settings(DATA_DIR=tmp_path))


def test_get_rule_evaluation_returns_artifact_content(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_rule_evaluation_json(123, {"summary": {"recommended_status": "needs_review"}})

    response = TestClient(app).get("/api/v1/runs/123/rule-evaluation")

    assert response.status_code == 200
    assert response.json()["artifact_type"] == "rule_evaluation"
    assert response.json()["content"]["summary"]["recommended_status"] == "needs_review"


def test_missing_rule_evaluation_returns_404(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_settings(monkeypatch, tmp_path)

    response = TestClient(app).get("/api/v1/runs/123/rule-evaluation")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "artifact_not_found"
