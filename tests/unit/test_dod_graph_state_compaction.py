"""Tests for the compact orchestration-state contract and merge behavior."""

from __future__ import annotations

from typing import Any

from backend.app.graphs import workflow
from backend.app.graphs.nodes import _merge_artifact_paths, validate_input_node
from backend.app.graphs.state import LEGACY_LARGE_STATE_KEYS
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def test_input_normalization_clears_legacy_large_state_values() -> None:
    state = validate_input_node(
        {
            "input": {"organization": "org", "project": "proj", "build_id": 7},
            "canonical_result": {"timeline": ["large"]},
            "evidence_result": {"bucket_3": {"descendants": ["large"]}},
        }
    )

    for key in LEGACY_LARGE_STATE_KEYS:
        assert state.get(key) in (None, {})
    assert state["input"] == {}


def test_artifact_references_replace_prior_values_without_accumulation() -> None:
    state = {
        "artifact_paths": {
            "canonical": "cosmos://run/canonical/old",
            "evidence_bundle": "cosmos://run/evidence/current",
        }
    }

    merged = _merge_artifact_paths(
        state,
        {"canonical": "cosmos://run/canonical/new"},
    )

    assert merged == {
        "canonical": "cosmos://run/canonical/new",
        "evidence_bundle": "cosmos://run/evidence/current",
    }
    assert isinstance(merged["canonical"], str)


def test_warnings_accumulate_intentionally_as_small_issue_dtos() -> None:
    state = validate_input_node(
        {
            "input": {"organization": "org", "project": "proj", "build_id": 7},
            "warnings": [
                {
                    "severity": "warning",
                    "code": "existing",
                    "message": "Existing warning.",
                    "phase": "input",
                }
            ],
        }
    )

    assert [item["code"] for item in state["warnings"]] == ["existing"]


def _checkpoint_state() -> dict[str, Any]:
    return {
        "run_id": "run-7",
        "build_id": 7,
        "organization": "org",
        "project": "proj",
        "mode": "pipeline",
        "status": "started",
        "artifact_paths": {},
        "warnings": [],
        "errors": [],
        "routing_decisions": [],
        "phase_durations_ms": {},
    }


def test_timed_node_records_soft_size_warning_once(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        workflow,
        "get_settings",
        lambda: Settings(DOD_GRAPH_STATE_WARN_BYTES=10, DOD_GRAPH_STATE_MAX_BYTES=10_000),
    )
    wrapped = workflow._timed_node(
        "test_phase",
        lambda _: {"canonical_summary": {"x": "secret-payload-value"}},
    )

    update = wrapped(_checkpoint_state())

    assert [item["code"] for item in update["warnings"]] == ["GRAPH_STATE_SIZE_WARNING"]
    assert "secret-payload-value" not in repr(update["warnings"][0]["diagnostics"])


def test_timed_node_compacts_oversized_update_before_checkpoint(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        workflow,
        "get_settings",
        lambda: Settings(DOD_GRAPH_STATE_WARN_BYTES=100, DOD_GRAPH_STATE_MAX_BYTES=200),
    )
    wrapped = workflow._timed_node(
        "test_phase",
        lambda _: {"service_now_payload": {"field": "large-value-" * 100}},
    )

    update = wrapped(_checkpoint_state())

    assert update["status"] == "failed"
    assert update["errors"][0]["code"] == "GRAPH_STATE_TOO_LARGE"
    assert update["service_now_payload"] is None
    assert "large-value" not in repr(update)
