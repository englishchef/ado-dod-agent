"""Health endpoint tests."""

from app.api.main import app
from app.core.config import Settings, get_settings
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def test_health_endpoint_returns_ok() -> None:
    """Health endpoint should return basic liveness payload."""

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "ado-dod-agent"


def test_runs_generate_placeholder_response() -> None:
    """Generate endpoint should remain a Phase-1 placeholder."""

    client = TestClient(app)
    response = client.post(
        "/api/v1/runs/generate",
        json={"organization": "org", "project": "proj", "build_id": 123, "mode": "local"},
    )

    assert response.status_code == 501
    payload = response.json()
    assert payload["status"] == "not_implemented"
    assert "Phase 2 supports raw metadata collection" in payload["message"]


def test_smoke_ado_auth_endpoint_returns_ok(monkeypatch: MonkeyPatch) -> None:
    """Smoke auth endpoint should support mocked auth ping without live Azure calls."""

    from app.api.routes import smoke as smoke_route

    class DummyTokenProvider:
        def __init__(self, settings: Settings) -> None:
            self._settings = settings

        async def get_auth_headers(self) -> dict[str, str]:
            return {"Authorization": "Bearer test-token", "Accept": "application/json"}

    monkeypatch.setattr(smoke_route, "AzureDevOpsTokenProvider", DummyTokenProvider)
    app.dependency_overrides[get_settings] = lambda: Settings(
        ADO_ORGANIZATION="org",
        ADO_PROJECT="project",
    )
    try:
        client = TestClient(app)
        response = client.get("/api/v1/smoke/ado-auth")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["authentication_succeeded"] is True
    assert payload["organization"] == "org"
    assert payload["project"] == "project"
