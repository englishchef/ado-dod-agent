"""Tests for smoke script helpers."""

from __future__ import annotations

import asyncio
from typing import Any

from backend.app.utils.config import Settings
from pytest import MonkeyPatch
from scripts import smoke_ado_auth


def test_build_safe_summary_and_format_output() -> None:
    """Smoke summary should include compact, expected fields."""

    summary = smoke_ado_auth.build_safe_summary(
        build={
            "id": 101,
            "definition": {"name": "Build Pipeline"},
            "sourceBranch": "refs/heads/main",
            "sourceVersion": "abc123",
            "status": "completed",
            "result": "succeeded",
            "requestedBy": {"displayName": "Jane Doe"},
        },
        timeline={"records": [{}, {}, {}]},
        work_items={"value": [{"id": 1}]},
        auth_succeeded=True,
    )
    rendered = smoke_ado_auth.format_summary(summary)

    assert summary["timeline_record_count"] == 3
    assert summary["linked_work_item_ref_count"] == 1
    assert "- authentication_succeeded: True" in rendered
    assert "- pipeline_name: Build Pipeline" in rendered


def test_run_smoke_with_mocked_client(monkeypatch: MonkeyPatch) -> None:
    """run_smoke should compose summary using mocked dependencies."""

    settings = Settings(ADO_ORGANIZATION="org", ADO_PROJECT="proj")

    class DummyTokenProvider:
        def __init__(self, **_: Any) -> None:
            pass

        async def get_auth_headers(self) -> dict[str, str]:
            return {"Authorization": "Bearer test-token", "Accept": "application/json"}

    class DummyBuildClient:
        def __init__(self, **_: Any) -> None:
            pass

        async def get_build(self, build_id: int) -> dict[str, Any]:
            return {"id": build_id, "definition": {"name": "Pipeline"}}

        async def get_build_timeline(self, build_id: int) -> dict[str, Any]:
            _ = build_id
            return {"records": [{}, {}]}

        async def get_build_work_items_refs(self, build_id: int) -> dict[str, Any]:
            _ = build_id
            return {"value": [{}]}

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(smoke_ado_auth, "get_settings", lambda: settings)
    monkeypatch.setattr(smoke_ado_auth, "configure_logging", lambda _: None)
    monkeypatch.setattr(smoke_ado_auth, "get_azure_credential", lambda _: object())
    monkeypatch.setattr(smoke_ado_auth, "AzureDevOpsTokenProvider", DummyTokenProvider)
    monkeypatch.setattr(smoke_ado_auth, "AzureDevOpsBuildClient", DummyBuildClient)

    summary = asyncio.run(smoke_ado_auth.run_smoke(build_id=9001, include_work_items=True))

    assert summary["authentication_succeeded"] is True
    assert summary["build_id"] == 9001
    assert summary["pipeline_name"] == "Pipeline"
    assert summary["timeline_record_count"] == 2
    assert summary["linked_work_item_ref_count"] == 1

