"""Canonical node tests for artifact-first compact state updates."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.graphs import nodes
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


class _Document:
    build_id = 7

    class _Run:
        pipeline_name = "pipeline"
        source_branch = "refs/heads/main"
        source_version = "abc"

    class _Items:
        work_items: list[Any] = []
        commits: list[Any] = []
        pull_requests: list[Any] = []

    class _Execution:
        stages: list[Any] = []
        jobs: list[Any] = []
        tasks: list[Any] = []
        artifacts: list[Any] = []

    class _Quality:
        test_runs: list[Any] = []
        failed_tests: list[Any] = []

    class _Risk:
        config_change_detected = False
        database_change_detected = False
        infrastructure_change_detected = False
        dependency_change_detected = False
        feature_flag_change_detected = False

    class _Metadata:
        warnings: list[str] = []

    run_context = _Run()
    change_context = _Items()
    execution_context = _Execution()
    quality_context = _Quality()
    risk_context = _Risk()
    normalization_metadata = _Metadata()

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return {
            "build_id": 7,
            "execution_context": {"tasks": [{"name": "large"}] * 100},
            "normalization_metadata": {"warnings": []},
        }


class _Store:
    def __init__(self) -> None:
        self.saved: dict[str, Any] = {}

    def raw_path(self, build_id: int, filename: str) -> str:
        return f"data/raw/{build_id}/{filename}"

    def load_raw_bundle(self, build_id: int) -> dict[str, Any]:
        return {"build_id": build_id, "raw": {}}

    def save_normalized_json(self, build_id: int, filename: str, payload: Any) -> str:
        self.saved[filename] = payload
        return f"cosmos://run-{build_id}/canonical"


def _state() -> nodes.DodGraphState:
    return {
        "run_id": "run-7",
        "build_id": 7,
        "organization": "org",
        "project": "proj",
        "mode": "pipeline",
        "status": "started",
        "artifact_paths": {"raw_bundle": "cosmos://run-7/raw_bundle"},
        "warnings": [],
        "errors": [],
    }


def test_canonical_artifact_is_persisted_and_not_duplicated_in_state(
    monkeypatch: MonkeyPatch,
) -> None:
    store = _Store()
    monkeypatch.setattr(nodes, "get_settings", lambda: Settings(DOD_STORAGE_BACKEND="local_json"))
    monkeypatch.setattr(nodes, "LocalJsonStore", lambda *_: store)
    monkeypatch.setattr(nodes, "normalize_raw_bundle", lambda *_, **__: _Document())

    update = nodes.normalize_canonical_node(_state())

    assert "canonical.json" in store.saved
    assert update["artifact_paths"]["canonical"] == "cosmos://run-7/canonical"
    assert update["canonical_summary"]["task_count"] == 0
    assert "canonical_result" not in update
    assert "execution_context" not in update


def test_canonical_failure_returns_compact_error_without_database_details(
    monkeypatch: MonkeyPatch,
    caplog: Any,
) -> None:
    class PGCosmosError(RuntimeError):
        pass

    store = _Store()
    monkeypatch.setattr(nodes, "get_settings", lambda: Settings(DOD_STORAGE_BACKEND="local_json"))
    monkeypatch.setattr(nodes, "LocalJsonStore", lambda *_: store)
    monkeypatch.setattr(
        nodes,
        "normalize_raw_bundle",
        lambda *_, **__: (_ for _ in ()).throw(
            PGCosmosError("raw database internals with secret-token-value")
        ),
    )

    with caplog.at_level(logging.ERROR):
        update = nodes.normalize_canonical_node(_state())
    rendered = repr(update)

    assert update["errors"][-1]["code"] == "canonical_normalization_failed"
    assert update["errors"][-1]["diagnostics"]["exception_type"] == "PGCosmosError"
    assert "raw database internals" not in rendered
    assert "secret-token-value" not in caplog.text
