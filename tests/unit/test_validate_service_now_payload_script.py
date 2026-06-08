"""Tests for Phase 6 validation CLI helpers."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.utils.config import Settings
from pytest import MonkeyPatch
from scripts import validate_service_now_payload


def valid_llm_outputs() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "build_id": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_metadata": {
            "provider": "azure_openai",
            "deployment": "deployment",
            "api_version": "2024-10-21",
            "auth_mode": "entra",
            "prompt_versions": {"bucket_1": "1.0", "bucket_2": "1.0", "bucket_3": "1.0"},
        },
        "bucket_1": {
            "change_description": "Change description",
            "short_change_description": "Short change",
            "justification": "Justification",
            "evidence_used": ["ref1"],
            "model_confidence": 0.8,
        },
        "bucket_2": {
            "testing_performed": "No automated test results were available.",
            "implementation_plan": "Implementation plan",
            "validation_plan": "Validation plan",
            "evidence_used": ["ref2"],
            "model_confidence": 0.7,
        },
        "bucket_3": {
            "backout_plan": "Backout plan",
            "risk_impact_analysis": "Risk analysis",
            "evidence_used": ["ref3"],
            "model_confidence": 0.6,
        },
    }


def evidence_bundle() -> dict[str, object]:
    return {
        "bucket_1": {
            "work_item_evidence": [],
            "commit_evidence": [{"id": "abc"}],
            "pull_request_evidence": [],
        },
        "bucket_2": {
            "test_evidence": {"total_tests": 0, "missing_test_context": ["missing"]},
            "artifact_evidence": [{"name": "drop"}],
        },
        "bucket_3": {
            "artifact_evidence": [{"name": "drop"}],
            "rollback_indicators": ["build"],
            "risk_flags": {"config_change_detected": False},
        },
    }


def test_script_loads_inputs_and_writes_outputs(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = data_dir / "output" / "9"
    evidence_dir = data_dir / "evidence" / "9"
    output_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (output_dir / "llm_outputs.json").write_text(json.dumps(valid_llm_outputs()), encoding="utf-8")
    (evidence_dir / "evidence_bundle.json").write_text(
        json.dumps(evidence_bundle()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validate_service_now_payload,
        "get_settings",
        lambda: Settings(DATA_DIR=data_dir),
    )
    args = argparse.Namespace(
        build_id=9,
        llm_outputs=None,
        evidence_bundle=None,
        allow_llm_repair=False,
    )

    summary = validate_service_now_payload.run_validation(args)

    assert Path(summary["output_paths"]["validated_output_path"]).exists()
    assert Path(summary["output_paths"]["service_now_payload_path"]).exists()
    assert Path(summary["output_paths"]["confidence_path"]).exists()
    assert Path(summary["output_paths"]["traceability_report_path"]).exists()


def test_script_main_exits_nonzero_on_validation_errors(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    output_dir = data_dir / "output" / "10"
    evidence_dir = data_dir / "evidence" / "10"
    output_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    outputs = valid_llm_outputs()
    outputs["bucket_1"]["justification"] = "TBD"  # type: ignore[index]
    (output_dir / "llm_outputs.json").write_text(json.dumps(outputs), encoding="utf-8")
    (evidence_dir / "evidence_bundle.json").write_text(
        json.dumps(evidence_bundle()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validate_service_now_payload,
        "get_settings",
        lambda: Settings(DATA_DIR=data_dir),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["validate_service_now_payload.py", "--build-id", "10"],
    )

    assert validate_service_now_payload.main() == 5


def test_script_main_exits_zero_on_warnings_only(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    output_dir = data_dir / "output" / "11"
    evidence_dir = data_dir / "evidence" / "11"
    output_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    (output_dir / "llm_outputs.json").write_text(json.dumps(valid_llm_outputs()), encoding="utf-8")
    (evidence_dir / "evidence_bundle.json").write_text(
        json.dumps(evidence_bundle()),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        validate_service_now_payload,
        "get_settings",
        lambda: Settings(DATA_DIR=data_dir),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["validate_service_now_payload.py", "--build-id", "11"],
    )

    assert validate_service_now_payload.main() == 0


def test_script_summary_does_not_print_tokens_or_authorization_headers() -> None:
    rendered = validate_service_now_payload.format_summary(
        {
            "build_id": 1,
            "is_valid": True,
            "issue_counts": {"info": 0, "warning": 0, "error": 0},
            "confidence": {"overall": 0.8, "bucket_1": 0.8, "bucket_2": 0.8, "bucket_3": 0.8},
            "output_paths": {
                "validated_output_path": "validated.json",
                "service_now_payload_path": "payload.json",
                "traceability_report_path": "traceability.json",
                "confidence_path": "confidence.json",
            },
        }
    ).lower()

    assert "token" not in rendered
    assert "authorization" not in rendered
    assert "bearer" not in rendered
    assert "traceability_report_path" in rendered
    assert "raw_reference_leakage_issue_count" in rendered
