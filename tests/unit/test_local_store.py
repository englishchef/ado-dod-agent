"""Tests for local JSON storage abstraction."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import Settings


def test_local_store_save_and_load_json(tmp_path: Path) -> None:
    """Store should save/load UTF-8 JSON under DATA_DIR."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    written_path = store.save_json(
        "raw/123/build.json",
        {"id": 123, "at": datetime(2026, 1, 1, tzinfo=UTC)},
    )

    loaded = store.load_json("raw/123/build.json")
    path_matches = written_path.endswith("raw\\123\\build.json") or written_path.endswith(
        "raw/123/build.json"
    )
    assert path_matches
    assert loaded["id"] == 123
    assert loaded["at"].startswith("2026-01-01")


def test_local_store_ensure_dirs_and_raw_path(tmp_path: Path) -> None:
    """Store should ensure run dirs and build canonical raw path."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    run_dir = store.ensure_run_dirs(42)
    expected_path = store.raw_path(42, "timeline.json")

    assert run_dir.exists()
    assert "raw" in expected_path
    assert "42" in expected_path


def test_local_store_normalized_helpers(tmp_path: Path) -> None:
    """Store should support normalized output helpers."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    normalized_path = store.normalized_path(9, "canonical.json")
    written = store.save_normalized_json(9, "canonical.json", {"build_id": 9})
    loaded = store.load_json("normalized/9/canonical.json")

    assert "normalized" in normalized_path
    assert written.endswith("canonical.json")
    assert loaded["build_id"] == 9


def test_local_store_load_raw_bundle(tmp_path: Path) -> None:
    """Store should load raw bundle by build id helper."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_json("raw/501/raw_bundle.json", {"build_id": 501, "raw": {}})

    payload = store.load_raw_bundle(501)
    assert payload["build_id"] == 501


def test_local_store_evidence_helpers(tmp_path: Path) -> None:
    """Store should support evidence output helper paths."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    evidence_path = store.evidence_path(22, "evidence_bundle.json")
    written = store.save_evidence_json(22, "evidence_bundle.json", {"build_id": 22})
    loaded = store.load_json("evidence/22/evidence_bundle.json")

    assert "evidence" in evidence_path
    assert written.endswith("evidence_bundle.json")
    assert loaded["build_id"] == 22


def test_local_store_load_canonical(tmp_path: Path) -> None:
    """Store should load canonical payload by build id helper."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_json("normalized/700/canonical.json", {"build_id": 700})

    payload = store.load_canonical(700)
    assert payload["build_id"] == 700


def test_local_store_output_helpers(tmp_path: Path) -> None:
    """Store should support generated output helper paths."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    output_path = store.output_path(88, "llm_outputs.json")
    written = store.save_output_json(88, "llm_outputs.json", {"build_id": 88})
    loaded = store.load_json("output/88/llm_outputs.json")

    assert "output" in output_path
    assert written.endswith("llm_outputs.json")
    assert loaded["build_id"] == 88


def test_local_store_load_evidence_bundle_and_bucket(tmp_path: Path) -> None:
    """Store should load Phase 4 evidence bundle and bucket helpers."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_evidence_json(90, "evidence_bundle.json", {"build_id": 90})
    store.save_evidence_json(90, "bucket_1_change_intent.json", {"target_fields": []})

    assert store.load_evidence_bundle(90)["build_id"] == 90
    assert store.load_evidence_bucket(90, "bucket_1_change_intent.json")["target_fields"] == []


def test_local_store_phase_6_helpers(tmp_path: Path) -> None:
    """Store should support Phase 6 output helpers."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_output_json(91, "llm_outputs.json", {"build_id": 91})
    validated_path = store.save_validated_output_json(91, {"is_valid": True})
    payload_path = store.save_service_now_payload_json(91, {"change_description": "x"})
    confidence_path = store.save_confidence_json(91, {"overall": 0.8})
    traceability_path = store.save_traceability_report_json(91, {"field_traceability": {}})
    rule_path = store.save_rule_evaluation_json(91, {"rules_triggered": []})

    assert store.load_llm_outputs(91)["build_id"] == 91
    assert store.load_service_now_payload(91)["change_description"] == "x"
    assert store.load_confidence(91)["overall"] == 0.8
    assert store.load_traceability_report(91)["field_traceability"] == {}
    assert store.load_rule_evaluation(91)["rules_triggered"] == []
    assert validated_path.endswith("validated_output.json")
    assert payload_path.endswith("service_now_payload.json")
    assert confidence_path.endswith("confidence.json")
    assert traceability_path.endswith("traceability_report.json")
    assert rule_path.endswith("rule_evaluation.json")
    assert store.traceability_report_path(91).endswith("traceability_report.json")
    assert store.rule_evaluation_path(91).endswith("rule_evaluation.json")
    assert store.artifact_exists(91, "confidence.json")


def test_local_store_run_summary_helpers(tmp_path: Path) -> None:
    """Store should support Phase 7A run summary helpers."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    path = store.save_run_summary_json(92, {"status": "completed"})

    assert store.run_summary_path(92).endswith("run_summary.json")
    assert path.endswith("run_summary.json")
    assert store.load_run_summary(92)["status"] == "completed"


def test_local_store_routing_decisions_helpers(tmp_path: Path) -> None:
    """Store should support Phase 7B routing decisions helpers."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    path = store.save_routing_decisions_json(93, {"decisions": []})

    assert store.routing_decisions_path(93).endswith("routing_decisions.json")
    assert path.endswith("routing_decisions.json")
    assert store.load_routing_decisions(93)["decisions"] == []

