"""Tests for Phase-2 raw metadata coordinator behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from app.collectors import raw_metadata
from app.core.config import Settings
from app.models.inputs import CollectRawInput
from app.models.raw import CollectorError, CollectorStatus
from pytest import MonkeyPatch


class DummyTokenProvider:
    def __init__(self, **_: Any) -> None:
        pass


class DummyClient:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    async def aclose(self) -> None:
        return None


def _patch_environment(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        raw_metadata,
        "get_settings",
        lambda: Settings(DATA_DIR=tmp_path, ADO_API_VERSION="7.1"),
    )
    monkeypatch.setattr(raw_metadata, "AzureDevOpsTokenProvider", DummyTokenProvider)
    monkeypatch.setattr(raw_metadata, "AzureDevOpsBuildClient", DummyClient)
    monkeypatch.setattr(raw_metadata, "AzureDevOpsWorkItemClient", DummyClient)
    monkeypatch.setattr(raw_metadata, "AzureDevOpsGitClient", DummyClient)
    monkeypatch.setattr(raw_metadata, "AzureDevOpsTestClient", DummyClient)


def test_run_context_failure_aborts_collection(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Run-context failure should produce failed collection result."""

    _patch_environment(monkeypatch, tmp_path)

    error = CollectorError(
        collector="run_context",
        message="build retrieval failed",
        severity="high",
    )

    async def fail_run_context(**_: Any) -> Any:
        raise RuntimeError(error.model_dump_json())

    monkeypatch.setattr(raw_metadata, "collect_run_context", fail_run_context)

    request = CollectRawInput(organization="org", project="proj", build_id=123)
    result = asyncio.run(raw_metadata.collect_raw_metadata(request))

    assert result.status == "failed"
    assert result.build_id == 123
    assert result.artifact_paths.raw_bundle is not None
    assert result.errors[0].collector == "run_context"


def test_optional_collector_failure_produces_partial(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Optional collector failure should produce partial final status."""

    _patch_environment(monkeypatch, tmp_path)

    async def ok_run_context(**_: Any) -> Any:
        return (
            {"build": {"id": 100, "definition": {"name": "Pipe"}}},
            CollectorStatus(name="run_context", status="completed", records_collected=1),
            [],
            {"build": str(tmp_path / "raw/100/build.json")},
        )

    async def ok_execution_context(**_: Any) -> Any:
        return (
            {"timeline": {"records": []}},
            CollectorStatus(name="execution_context", status="completed", records_collected=1),
            [],
            {"timeline": str(tmp_path / "raw/100/timeline.json")},
        )

    async def partial_change_context(**_: Any) -> Any:
        return (
            {
                "work_item_refs": {"count": 0, "value": []},
                "work_items": {"count": 0, "value": []},
                "changes": {"count": 0, "value": []},
                "pull_requests": {"pull_requests": []},
            },
            CollectorStatus(name="change_context", status="partial", records_collected=0),
            [CollectorError(collector="change_context", message="work item hydration failed")],
            {},
        )

    async def ok_quality_context(**_: Any) -> Any:
        return (
            {"test_runs": {"count": 0, "value": []}, "test_results": {"count": 0, "value": []}},
            CollectorStatus(name="quality_context", status="completed", records_collected=1),
            [],
            {},
        )

    monkeypatch.setattr(raw_metadata, "collect_run_context", ok_run_context)
    monkeypatch.setattr(raw_metadata, "collect_execution_context", ok_execution_context)
    monkeypatch.setattr(raw_metadata, "collect_change_context", partial_change_context)
    monkeypatch.setattr(raw_metadata, "collect_quality_context", ok_quality_context)

    request = CollectRawInput(organization="org", project="proj", build_id=100)
    result = asyncio.run(raw_metadata.collect_raw_metadata(request))

    assert result.status == "partial"
    assert any(error.collector == "change_context" for error in result.errors)


def test_raw_bundle_contains_expected_top_keys(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """raw_bundle should contain expected root keys."""

    _patch_environment(monkeypatch, tmp_path)

    async def ok_run_context(**_: Any) -> Any:
        return (
            {"build": {"id": 11}},
            CollectorStatus(name="run_context", status="completed", records_collected=1),
            [],
            {},
        )

    async def noop_collector(**_: Any) -> Any:
        return ({}, CollectorStatus(name="noop", status="completed", records_collected=0), [], {})

    monkeypatch.setattr(raw_metadata, "collect_run_context", ok_run_context)
    monkeypatch.setattr(raw_metadata, "collect_execution_context", noop_collector)
    monkeypatch.setattr(raw_metadata, "collect_change_context", noop_collector)
    monkeypatch.setattr(raw_metadata, "collect_quality_context", noop_collector)

    request = CollectRawInput(organization="org", project="proj", build_id=11)
    result = asyncio.run(raw_metadata.collect_raw_metadata(request))

    bundle_path = result.artifact_paths.raw_bundle
    assert bundle_path is not None
    bundle_content = Path(bundle_path).read_text(encoding="utf-8")
    assert '"collection_run_id"' in bundle_content
    assert '"collector_statuses"' in bundle_content
    assert '"errors"' in bundle_content
    assert '"raw"' in bundle_content


def test_collect_raw_metadata_writes_expected_artifact_paths(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Coordinator should return key artifact paths for mandatory files."""

    _patch_environment(monkeypatch, tmp_path)

    async def ok_run_context(**_: Any) -> Any:
        return (
            {"build": {"id": 77}},
            CollectorStatus(name="run_context", status="completed", records_collected=1),
            [],
            {"build": str(tmp_path / "raw/77/build.json")},
        )

    async def ok_execution_context(**_: Any) -> Any:
        return (
            {"timeline": {"records": []}},
            CollectorStatus(name="execution_context", status="completed", records_collected=1),
            [],
            {"timeline": str(tmp_path / "raw/77/timeline.json")},
        )

    async def ok_change_context(**_: Any) -> Any:
        return (
            {
                "work_item_refs": {"count": 0, "value": []},
                "changes": {"count": 0, "value": []},
                "work_items": {"count": 0, "value": []},
                "pull_requests": {"pull_requests": []},
            },
            CollectorStatus(name="change_context", status="completed", records_collected=1),
            [],
            {
                "work_item_refs": str(tmp_path / "raw/77/work_item_refs.json"),
                "changes": str(tmp_path / "raw/77/changes.json"),
            },
        )

    async def ok_quality_context(**_: Any) -> Any:
        return (
            {"test_runs": {"count": 0, "value": []}, "test_results": {"count": 0, "value": []}},
            CollectorStatus(name="quality_context", status="completed", records_collected=1),
            [],
            {},
        )

    monkeypatch.setattr(raw_metadata, "collect_run_context", ok_run_context)
    monkeypatch.setattr(raw_metadata, "collect_execution_context", ok_execution_context)
    monkeypatch.setattr(raw_metadata, "collect_change_context", ok_change_context)
    monkeypatch.setattr(raw_metadata, "collect_quality_context", ok_quality_context)

    request = CollectRawInput(organization="org", project="proj", build_id=77)
    result = asyncio.run(raw_metadata.collect_raw_metadata(request))

    assert result.artifact_paths.build is not None
    assert result.artifact_paths.timeline is not None
    assert result.artifact_paths.work_item_refs is not None
    assert result.artifact_paths.changes is not None
    assert result.artifact_paths.raw_bundle is not None
