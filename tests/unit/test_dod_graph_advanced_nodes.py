"""Tests for Phase 7B advanced graph nodes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.graphs import nodes
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def _state() -> nodes.DodGraphState:
    return {
        "run_id": "dod-run-20260528T010203Z-5",
        "build_id": 5,
        "organization": "org",
        "project": "proj",
        "mode": "local",
        "input": {},
        "status": "started",
        "started_at": "2026-05-28T00:00:00+00:00",
        "artifact_paths": {},
        "warnings": [],
        "errors": [],
        "routing_decisions": [],
        "evidence_result": _evidence_bundle(),
    }


def _evidence_bundle() -> dict[str, Any]:
    return {
        "build_id": 5,
        "bucket_1": {
            "work_item_evidence": [{"title": "Feature"}],
            "commit_evidence": [{"message": "fix"}],
        },
        "bucket_2": {
            "stage_evidence": [{"name": "Deploy"}],
            "test_evidence": {"total_tests": 0, "missing_test_context": ["missing"]},
            "validation_signals": ["Validate"],
            "deployment_signals": ["Deploy"],
        },
        "bucket_3": {
            "service_context": {"source_version": "abc"},
            "artifact_evidence": [],
            "rollback_indicators": [],
            "risk_flags": {"database_change_detected": True},
            "failed_or_warning_evidence": [],
        },
    }


def test_assess_evidence_quality_node_populates_state() -> None:
    result = nodes.assess_evidence_quality_node(_state())
    evidence_quality = result["evidence_quality"]
    assert isinstance(evidence_quality, dict)

    assert evidence_quality["bucket_1_quality"] == "strong"
    assert len(result["routing_decisions"]) == 3


def test_assess_risk_tier_node_populates_state() -> None:
    result = nodes.assess_risk_tier_node(_state())
    risk_tier = result["risk_tier"]
    assert isinstance(risk_tier, dict)

    assert risk_tier["risk_tier"] == "high"
    assert result["routing_decisions"][0]["step"] == "risk_tier"


def test_select_prompt_strategy_node_populates_state() -> None:
    state = _state()
    state["evidence_quality"] = nodes.assess_evidence_quality_node(state)["evidence_quality"]
    state["risk_tier"] = nodes.assess_risk_tier_node(state)["risk_tier"]

    result = nodes.select_prompt_strategy_node(state)
    prompt_strategy = result["prompt_strategy"]
    assert isinstance(prompt_strategy, dict)

    assert prompt_strategy["bucket_2_strategy"] == "bucket_2_missing_tests"
    assert prompt_strategy["bucket_3_strategy"] == "bucket_3_high_risk"


def test_persist_routing_decisions_node_writes_artifact(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(nodes, "get_settings", lambda: Settings(DATA_DIR=tmp_path))
    state = _state()
    state["evidence_quality"] = nodes.assess_evidence_quality_node(state)["evidence_quality"]
    state["risk_tier"] = nodes.assess_risk_tier_node(state)["risk_tier"]
    state["prompt_strategy"] = nodes.select_prompt_strategy_node(
        {
            **state,
            "evidence_quality": state["evidence_quality"],
            "risk_tier": state["risk_tier"],
        }
    )["prompt_strategy"]

    result = nodes.persist_routing_decisions_node(state)

    assert Path(result["artifact_paths"]["routing_decisions"]).exists()
    assert "routing_decisions_bundle" not in result


def test_generate_llm_outputs_node_appends_retry_decision(monkeypatch: MonkeyPatch) -> None:
    class FakeOutputs:
        bucket_1 = _FakeModel({"change_description": "x"})
        bucket_2 = _FakeModel({"testing_performed": "x"})
        bucket_3 = _FakeModel({"backout_plan": "x"})

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return {"build_id": 5, "bucket_1": {}, "bucket_2": {}, "bucket_3": {}}

    def fake_generate_all_buckets(**kwargs: Any) -> FakeOutputs:
        kwargs["on_bucket_retry"]("bucket_2", 1, RuntimeError("transient"))
        return FakeOutputs()

    monkeypatch.setattr(nodes, "generate_all_buckets", fake_generate_all_buckets)
    result = nodes.generate_llm_outputs_node(_state())

    assert result["routing_decisions"][0]["decision"] == "bucket_2_retry"


def test_assemble_run_result_needs_review_for_high_risk_low_confidence(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(nodes, "get_settings", lambda: Settings(DATA_DIR=tmp_path))
    state = _state()
    state["service_now_payload"] = {"change_description": "x"}
    state["confidence"] = {"overall": 0.8}
    state["risk_tier"] = {"risk_tier": "high"}

    result = nodes.assemble_run_result_node(state)

    assert result["status"] == "needs_review"


class _FakeModel:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return self._payload
