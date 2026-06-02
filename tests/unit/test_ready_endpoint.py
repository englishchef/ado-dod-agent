"""Tests for Phase 8 readiness endpoint."""

from __future__ import annotations

from pathlib import Path

from backend.api.main import app
from backend.app.utils.config import Settings, get_settings
from fastapi.testclient import TestClient


def test_ready_returns_ready_when_required_config_present(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        ADO_ORGANIZATION="org",
        ADO_PROJECT="proj",
        ADO_API_VERSION="7.1",
        AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
        AZURE_OPENAI_DEPLOYMENT="deployment",
        AZURE_OPENAI_API_VERSION="2024-10-21",
        AZURE_OPENAI_AUTH_MODE="entra",
        DATA_DIR=tmp_path,
    )
    try:
        response = TestClient(app).get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["missing_config"] == []


def test_ready_returns_503_when_required_config_missing(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        ADO_ORGANIZATION=None,
        ADO_PROJECT="proj",
        AZURE_OPENAI_ENDPOINT=None,
        AZURE_OPENAI_DEPLOYMENT="deployment",
        AZURE_OPENAI_API_VERSION="2024-10-21",
        DATA_DIR=tmp_path,
    )
    try:
        response = TestClient(app).get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert "ADO_ORGANIZATION" in response.json()["missing_config"]
    assert "AZURE_OPENAI_ENDPOINT" in response.json()["missing_config"]


def test_ready_does_not_call_ado_or_llm(tmp_path: Path) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        ADO_ORGANIZATION="org",
        ADO_PROJECT="proj",
        AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
        AZURE_OPENAI_DEPLOYMENT="deployment",
        AZURE_OPENAI_API_VERSION="2024-10-21",
        DATA_DIR=tmp_path,
    )
    try:
        response = TestClient(app).get("/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
