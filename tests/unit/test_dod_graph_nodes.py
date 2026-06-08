"""Tests for Phase 7A graph nodes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from backend.app.graphs import nodes
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def _base_state() -> nodes.DodGraphState:
    return {
        "run_id": "dod-run-20260527T010203Z-7",
        "build_id": 7,
        "organization": "org",
        "project": "proj",
        "mode": "local",
        "input": {},
        "status": "started",
        "started_at": "2026-05-27T00:00:00+00:00",
        "artifact_paths": {},
        "warnings": [],
        "errors": [],
    }


def _state(**updates: Any) -> nodes.DodGraphState:
    return cast(nodes.DodGraphState, {**_base_state(), **updates})


@dataclass
class FakeModel:
    payload: dict[str, Any]

    def model_dump(self, mode: str = "python") -> dict[str, Any]:
        return self.payload


class FakeStore:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.saved: dict[str, Any] = {}

    def raw_path(self, build_id: int, filename: str) -> str:
        return f"data/raw/{build_id}/{filename}"

    def normalized_path(self, build_id: int, filename: str) -> str:
        return f"data/normalized/{build_id}/{filename}"

    def evidence_path(self, build_id: int, filename: str) -> str:
        return f"data/evidence/{build_id}/{filename}"

    def output_path(self, build_id: int, filename: str) -> str:
        return f"data/output/{build_id}/{filename}"

    def load_raw_bundle(self, build_id: int) -> dict[str, Any]:
        return {"build_id": build_id, "raw": {"build": {"id": build_id}}}

    def load_canonical(self, build_id: int) -> dict[str, Any]:
        return {"build_id": build_id}

    def load_evidence_bundle(self, build_id: int) -> dict[str, Any]:
        return {"build_id": build_id, "bucket_1": {}, "bucket_2": {}, "bucket_3": {}}

    def load_llm_outputs(self, build_id: int) -> dict[str, Any]:
        return {"build_id": build_id}

    def load_service_now_payload(self, build_id: int) -> dict[str, Any]:
        return {"change_description": "Change"}

    def load_validated_output(self, build_id: int) -> dict[str, Any]:
        return {"build_id": build_id}

    def load_confidence(self, build_id: int) -> dict[str, Any]:
        return {"overall": 0.8}

    def load_routing_decisions(self, build_id: int) -> dict[str, Any]:
        return {"decisions": []}

    def load_traceability_report(self, build_id: int) -> dict[str, Any]:
        return {"field_traceability": {}}

    def save_normalized_json(self, build_id: int, filename: str, payload: Any) -> str:
        self.saved[filename] = payload
        return self.normalized_path(build_id, filename)

    def save_evidence_json(self, build_id: int, filename: str, payload: Any) -> str:
        self.saved[filename] = payload
        return self.evidence_path(build_id, filename)

    def save_output_json(self, build_id: int, filename: str, payload: Any) -> str:
        self.saved[filename] = payload
        return self.output_path(build_id, filename)

    def save_validated_output_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "validated_output.json", payload)

    def save_service_now_payload_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "service_now_payload.json", payload)

    def save_confidence_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "confidence.json", payload)

    def save_traceability_report_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "traceability_report.json", payload)

    def save_rule_evaluation_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "rule_evaluation.json", payload)

    def save_run_summary_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "run_summary.json", payload)


def test_collect_raw_metadata_node_updates_result_and_paths(monkeypatch: MonkeyPatch) -> None:
    async def fake_collect(_: Any) -> dict[str, Any]:
        return {
            "status": "completed",
            "artifact_paths": {"raw_bundle": "data/raw/7/raw_bundle.json"},
            "collector_statuses": [],
            "errors": [],
        }

    monkeypatch.setattr(nodes, "collect_raw_metadata", fake_collect)

    state = nodes.collect_raw_metadata_node(_base_state())

    raw_result = state["raw_result"]
    assert isinstance(raw_result, dict)
    assert raw_result["status"] == "completed"
    assert state["artifact_paths"]["raw_bundle"].endswith("raw_bundle.json")


def test_collect_raw_metadata_node_sets_failed_on_hard_error(monkeypatch: MonkeyPatch) -> None:
    async def fake_collect(_: Any) -> dict[str, Any]:
        return {
            "status": "failed",
            "artifact_paths": {"raw_bundle": "data/raw/7/raw_bundle.json"},
            "collector_statuses": [{"name": "run_context", "status": "failed"}],
            "errors": [{"collector": "run_context", "message": "build retrieval failed"}],
        }

    monkeypatch.setattr(nodes, "collect_raw_metadata", fake_collect)

    state = nodes.collect_raw_metadata_node(_base_state())

    assert state["status"] == "failed"
    assert state["errors"][0]["phase"] == "collect_raw"


def test_normalize_canonical_node_updates_canonical_result(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(nodes, "LocalJsonStore", FakeStore)
    monkeypatch.setattr(
        nodes,
        "normalize_raw_bundle",
        lambda *_, **__: FakeModel(
            {
                "build_id": 7,
                "normalization_metadata": {"warnings": ["some_raw_sections_missing"]},
            }
        ),
    )

    state = nodes.normalize_canonical_node(_base_state())

    canonical_result = state["canonical_result"]
    assert isinstance(canonical_result, dict)
    assert canonical_result["build_id"] == 7
    assert state["artifact_paths"]["canonical"].endswith("canonical.json")
    assert state["warnings"][0]["phase"] == "normalize"


def test_build_evidence_buckets_node_updates_evidence_result(monkeypatch: MonkeyPatch) -> None:
    class FakeCanonical:
        @staticmethod
        def model_validate(_: Any) -> object:
            return object()

    class FakeBundle:
        bucket_1 = FakeModel({"bucket": 1})
        bucket_2 = FakeModel({"bucket": 2})
        bucket_3 = FakeModel({"bucket": 3})

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return {
                "build_id": 7,
                "generation_metadata": {
                    "warnings": ["bucket_1_has_gaps"],
                    "missing_sections": ["no PR metadata found"],
                },
            }

    monkeypatch.setattr(nodes, "LocalJsonStore", FakeStore)
    monkeypatch.setattr(nodes, "CanonicalDodDocument", FakeCanonical)
    monkeypatch.setattr(nodes, "build_evidence_bundle", lambda *_, **__: FakeBundle())

    state = nodes.build_evidence_buckets_node(_state(canonical_result={"x": "y"}))

    evidence_result = state["evidence_result"]
    assert isinstance(evidence_result, dict)
    assert evidence_result["build_id"] == 7
    assert state["artifact_paths"]["evidence_bundle"].endswith("evidence_bundle.json")
    assert len(state["warnings"]) == 2


def test_generate_llm_outputs_node_updates_outputs(monkeypatch: MonkeyPatch) -> None:
    outputs = _fake_llm_outputs()
    monkeypatch.setattr(nodes, "LocalJsonStore", FakeStore)
    monkeypatch.setattr(nodes, "generate_all_buckets", lambda **_: outputs)

    state = nodes.generate_llm_outputs_node(_state(evidence_result={}))

    llm_outputs = state["llm_outputs"]
    assert isinstance(llm_outputs, dict)
    assert llm_outputs["build_id"] == 7
    assert state["artifact_paths"]["llm_outputs"].endswith("llm_outputs.json")


def test_generate_llm_outputs_node_retries_once(monkeypatch: MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_generate(**_: Any) -> Any:
        calls["count"] += 1
        kwargs = _
        kwargs["on_bucket_retry"]("bucket_2", 1, RuntimeError("transient"))
        return _fake_llm_outputs()

    monkeypatch.setattr(nodes, "LocalJsonStore", FakeStore)
    monkeypatch.setattr(nodes, "generate_all_buckets", fake_generate)

    state = nodes.generate_llm_outputs_node(_state(evidence_result={}))

    assert calls["count"] == 1
    assert "status" not in state
    assert state["routing_decisions"][0]["decision"] == "bucket_2_retry"


def test_validate_outputs_node_stores_payload_and_confidence(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(nodes, "LocalJsonStore", FakeStore)
    monkeypatch.setattr(nodes, "validate_and_assemble_outputs", lambda **_: _fake_validated())

    state = nodes.validate_outputs_node(
        _state(llm_outputs={"build_id": 7}, evidence_result={})
    )

    service_now_payload = state["service_now_payload"]
    confidence = state["confidence"]
    assert isinstance(service_now_payload, dict)
    assert isinstance(confidence, dict)
    assert service_now_payload["change_description"] == "Change"
    assert confidence["overall"] == 0.8
    assert state["artifact_paths"]["confidence"].endswith("confidence.json")
    assert state["artifact_paths"]["traceability_report"].endswith("traceability_report.json")


def test_evaluate_rules_node_stores_rule_evaluation(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(nodes, "LocalJsonStore", FakeStore)

    state = nodes.evaluate_rules_node(
        _state(
            evidence_result={"bucket_2": {}, "bucket_3": {}},
            service_now_payload={
                "change_description": "Change",
                "short_change_description": "Short",
                "justification": "Justification",
                "testing_performed": "No automated tests were available.",
                "implementation_plan": "Deploy via pipeline.",
                "validation_plan": "Validate API health.",
                "backout_plan": "Redeploy previous build.",
                "risk_impact_analysis": "No specific risk signals were detected.",
            },
            llm_outputs={},
            confidence={"overall": 0.8},
        )
    )

    assert state["artifact_paths"]["rule_evaluation"].endswith("rule_evaluation.json")
    rule_evaluation = state.get("rule_evaluation")
    assert isinstance(rule_evaluation, dict)
    assert rule_evaluation["summary"]["triggered_rule_count"] >= 0


def test_assemble_run_result_status_rules(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(nodes, "get_settings", lambda: Settings(DATA_DIR=tmp_path))

    assert (
        nodes.assemble_run_result_node(
            _state(confidence={"overall": 0.8}, service_now_payload={"x": "y"})
        )["status"]
        == "completed"
    )
    assert (
        nodes.assemble_run_result_node(
            _state(
                warnings=[{"severity": "warning"}],
                confidence={"overall": 0.8},
                service_now_payload={"x": "y"},
            )
        )["status"]
        == "completed_with_warnings"
    )
    assert (
        nodes.assemble_run_result_node(
            _state(confidence={"overall": 0.4}, service_now_payload={"x": "y"})
        )["status"]
        == "needs_review"
    )
    failed_state = nodes.assemble_run_result_node(_state(status="failed"))
    assert failed_state["status"] == "failed"


def _fake_llm_outputs() -> Any:
    class Outputs:
        bucket_1 = FakeModel({"change_description": "Change"})
        bucket_2 = FakeModel({"testing_performed": "Tests"})
        bucket_3 = FakeModel({"backout_plan": "Backout"})

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return {"build_id": 7, "bucket_1": {}, "bucket_2": {}, "bucket_3": {}}

    return Outputs()


def _fake_validated() -> Any:
    class Validated:
        service_now_payload = FakeModel({"change_description": "Change"})
        confidence = FakeModel({"overall": 0.8, "bucket_1": 0.8, "bucket_2": 0.8, "bucket_3": 0.8})

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return {
                "build_id": 7,
                "service_now_payload": self.service_now_payload.model_dump(),
                "confidence": self.confidence.model_dump(),
                "validation_issues": [],
            }

    return Validated()
