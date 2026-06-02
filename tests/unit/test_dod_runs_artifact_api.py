"""Tests for Phase 8 read-only artifact endpoints."""

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


def test_get_summary_returns_run_summary_content(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_run_summary_json(123, {"run_id": "run-1", "status": "completed"})

    response = TestClient(app).get("/api/v1/runs/123/summary")

    assert response.status_code == 200
    assert response.json()["content"]["run_id"] == "run-1"


def test_get_payload_returns_service_now_payload_content(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_service_now_payload_json(123, {"change_description": "Change"})

    response = TestClient(app).get("/api/v1/runs/123/payload")

    assert response.status_code == 200
    assert response.json()["content"]["change_description"] == "Change"


def test_get_confidence_returns_confidence_content(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_confidence_json(123, {"overall": 0.8})

    response = TestClient(app).get("/api/v1/runs/123/confidence")

    assert response.status_code == 200
    assert response.json()["content"]["overall"] == 0.8


def test_get_routing_decisions_returns_routing_content(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_settings(monkeypatch, tmp_path)
    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_routing_decisions_json(123, {"decisions": []})

    response = TestClient(app).get("/api/v1/runs/123/routing-decisions")

    assert response.status_code == 200
    assert response.json()["content"]["decisions"] == []


def test_missing_artifact_returns_404(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _patch_settings(monkeypatch, tmp_path)

    response = TestClient(app).get("/api/v1/runs/123/payload")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "artifact_not_found"
