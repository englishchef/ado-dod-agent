"""Tests for shared DoD run contract models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import pytest
from backend.app.models.dod_contracts import (
    DoDRunInput,
    normalize_dod_run_input,
    serialize_dod_run_output,
)
from backend.app.models.run_summary import DodRunSummary
from pydantic import ValidationError


def test_dod_run_input_valid_input_passes() -> None:
    run_input = DoDRunInput(
        organization=" org ",
        project=" proj ",
        build_id=123,
        mode="pipeline",
        correlation_id="corr-1",
        metadata={"source": "ado"},
    )

    assert run_input.organization == "org"
    assert run_input.project == "proj"
    assert run_input.correlation_id == "corr-1"


def test_dod_run_input_defaults_mode_and_metadata() -> None:
    run_input = normalize_dod_run_input(
        {"organization": "org", "project": "proj", "build_id": 123}
    )

    assert run_input.mode == "pipeline"
    assert run_input.metadata == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"project": "proj", "build_id": 123},
        {"organization": "", "project": "proj", "build_id": 123},
        {"organization": "org", "build_id": 123},
        {"organization": "org", "project": "", "build_id": 123},
        {"organization": "org", "project": "proj"},
        {"organization": "org", "project": "proj", "build_id": 0},
        {"organization": "org", "project": "proj", "build_id": 123, "mode": "dev"},
    ],
)
def test_dod_run_input_rejects_invalid_payloads(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        normalize_dod_run_input(payload)


def test_dict_result_serializes_and_derives_rule_summary() -> None:
    output = serialize_dod_run_output(
        {
            "run_id": "run-1",
            "build_id": 123,
            "status": "completed_with_warnings",
            "service_now_payload": {"change_description": "Change"},
            "confidence": {"overall": 0.8},
            "rule_evaluation": {
                "rules_triggered": [
                    {"severity": "warning"},
                    {"severity": "review"},
                    {"severity": "error"},
                ],
                "test_completeness_score": {"overall_score": 0.5},
            },
            "artifact_paths": {"run_summary": "summary.json"},
            "warnings": [{"severity": "warning", "code": "gap"}],
            "errors": [],
            "evidence_bundle": {"raw": "should not be copied"},
        }
    )

    assert output.run_id == "run-1"
    assert output.rule_evaluation_summary["highest_severity"] == "error"
    assert output.rule_evaluation_summary["triggered_rule_count"] == 3
    assert output.rule_evaluation_summary["test_completeness_score"]["overall_score"] == 0.5
    assert output.artifact_paths == {"run_summary": "summary.json"}
    assert output.warnings[0]["code"] == "gap"
    assert output.errors == []
    assert output.result is not None
    assert "evidence_bundle" not in output.result


def test_pydantic_result_serializes() -> None:
    summary = DodRunSummary(
        run_id="run-2",
        build_id=456,
        organization="org",
        project="proj",
        status="completed",
        started_at=datetime(2026, 6, 1, tzinfo=UTC),
        service_now_payload=None,
        confidence=None,
        artifact_paths={},
        warnings=[],
        errors=[],
    )

    output = serialize_dod_run_output(summary)

    assert output.run_id == "run-2"
    assert output.build_id == 456
    assert output.service_now_payload == {}
    assert output.confidence == {}


def test_dataclass_result_serializes() -> None:
    @dataclass
    class FakeResult:
        run_id: str
        build_id: int
        status: str
        artifact_paths: dict[str, str]

    output = serialize_dod_run_output(
        FakeResult(
            run_id="run-3",
            build_id=789,
            status="needs_review",
            artifact_paths={"rule_evaluation": "rules.json"},
        )
    )

    assert output.run_id == "run-3"
    assert output.status == "needs_review"
    assert output.artifact_paths["rule_evaluation"] == "rules.json"


def test_missing_optional_fields_default_safely() -> None:
    run_input = normalize_dod_run_input({"organization": "org", "project": "proj", "build_id": 7})

    output = serialize_dod_run_output({"status": "error"}, fallback_input=run_input)

    assert output.build_id == 7
    assert output.status == "error"
    assert output.service_now_payload == {}
    assert output.confidence == {}
    assert output.artifact_paths == {}
    assert output.warnings == []
    assert output.errors == []
