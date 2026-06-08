"""Tests for Phase 7B advanced workflow routing."""

from __future__ import annotations

from typing import Any

from backend.app.graphs import workflow
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def _input() -> dict[str, Any]:
    return {"organization": "org", "project": "proj", "build_id": 42, "mode": "local"}


def _patch_common(monkeypatch: MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setattr(
        "backend.app.graphs.nodes.get_settings",
        lambda: Settings(DATA_DIR=tmp_path),
    )
    monkeypatch.setattr(
        workflow,
        "collect_raw_metadata_node",
        lambda state: {"raw_result": {}, "artifact_paths": {"raw_bundle": "raw.json"}},
    )
    monkeypatch.setattr(
        workflow,
        "normalize_canonical_node",
        lambda state: {
            "canonical_result": {},
            "artifact_paths": {**state["artifact_paths"], "canonical": "canonical.json"},
        },
    )
    monkeypatch.setattr(
        workflow,
        "build_evidence_buckets_node",
        lambda state: {
            "evidence_result": {},
            "artifact_paths": {**state["artifact_paths"], "evidence_bundle": "evidence.json"},
        },
    )
    monkeypatch.setattr(
        workflow,
        "generate_llm_outputs_node",
        lambda state: {
            "llm_outputs": {},
            "artifact_paths": {**state["artifact_paths"], "llm_outputs": "llm.json"},
        },
    )
    monkeypatch.setattr(
        workflow,
        "validate_outputs_node",
        lambda state: {
            "service_now_payload": {"change_description": "x"},
            "confidence": {"overall": 0.9},
            "artifact_paths": {
                **state["artifact_paths"],
                "validated_output": "validated.json",
                "service_now_payload": "payload.json",
                "confidence": "confidence.json",
            },
        },
    )
    monkeypatch.setattr(
        workflow,
        "evaluate_rules_node",
        lambda state: {
            "rule_evaluation": {"summary": {"recommended_status": "completed"}},
            "artifact_paths": {**state["artifact_paths"], "rule_evaluation": "rules.json"},
        },
    )


def test_workflow_happy_path_creates_routing_decisions(
    monkeypatch: MonkeyPatch,
    tmp_path: Any,
) -> None:
    _patch_common(monkeypatch, tmp_path)

    result = workflow.run_dod_workflow(_input())

    assert result["status"] in {"completed", "completed_with_warnings", "needs_review"}
    assert result["artifact_paths"]["routing_decisions"].endswith("routing_decisions.json")


def test_missing_tests_route_to_bucket_2_missing_tests(
    monkeypatch: MonkeyPatch,
    tmp_path: Any,
) -> None:
    _patch_common(monkeypatch, tmp_path)
    captured: dict[str, Any] = {}

    def fake_generate(state: dict[str, Any]) -> dict[str, Any]:
        captured.update(state.get("prompt_strategy") or {})
        return {"llm_outputs": {}}

    monkeypatch.setattr(workflow, "generate_llm_outputs_node", fake_generate)

    workflow.run_dod_workflow(_input())

    assert captured["bucket_2_strategy"] == "bucket_2_missing_tests"


def test_high_risk_sets_needs_review_when_confidence_below_threshold(
    monkeypatch: MonkeyPatch,
    tmp_path: Any,
) -> None:
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(
        workflow,
        "assess_risk_tier_node",
        lambda state: {"risk_tier": {"risk_tier": "high"}},
    )
    monkeypatch.setattr(
        workflow,
        "validate_outputs_node",
        lambda state: {
            "service_now_payload": {"change_description": "x"},
            "confidence": {"overall": 0.8},
        },
    )

    result = workflow.run_dod_workflow(_input())

    assert result["status"] == "needs_review"


def test_failed_llm_bucket_after_retry_results_failed(
    monkeypatch: MonkeyPatch,
    tmp_path: Any,
) -> None:
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(
        workflow,
        "generate_llm_outputs_node",
        lambda state: {"status": "failed", "errors": [{"severity": "error", "code": "llm"}]},
    )

    result = workflow.run_dod_workflow(_input())

    assert result["status"] == "failed"
    assert result["artifact_paths"]["routing_decisions"].endswith("routing_decisions.json")


def test_completed_with_warnings_still_works(
    monkeypatch: MonkeyPatch,
    tmp_path: Any,
) -> None:
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setattr(
        workflow,
        "validate_outputs_node",
        lambda state: {
            "warnings": [{"severity": "warning", "code": "validation_warning"}],
            "service_now_payload": {"change_description": "x"},
            "confidence": {"overall": 0.9},
        },
    )

    result = workflow.run_dod_workflow(_input())

    assert result["status"] == "completed_with_warnings"
