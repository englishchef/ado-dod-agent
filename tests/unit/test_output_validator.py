"""Tests for deterministic Phase 6 output validation."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from backend.app.models.validated_outputs import ValidationIssue
from backend.app.services.validation.output_validator import validate_llm_outputs


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


def _issues(outputs: dict[str, object] | None = None) -> list[ValidationIssue]:
    results = validate_llm_outputs(outputs or valid_llm_outputs(), evidence_bundle())
    return [issue for result in results for issue in result.issues]


def test_valid_llm_outputs_pass_without_errors() -> None:
    issues = _issues()

    assert not any(issue.severity == "error" for issue in issues)


def test_missing_required_field_creates_error() -> None:
    outputs = deepcopy(valid_llm_outputs())
    bucket_1 = outputs["bucket_1"]
    assert isinstance(bucket_1, dict)
    del bucket_1["justification"]  # type: ignore[index]

    issues = _issues(outputs)

    assert any(issue.code == "missing_required_field" for issue in issues)


def test_placeholder_field_creates_error() -> None:
    outputs = deepcopy(valid_llm_outputs())
    outputs["bucket_1"]["justification"] = "TBD"  # type: ignore[index]

    issues = _issues(outputs)

    assert any(issue.code == "placeholder_field" for issue in issues)


def test_unsupported_test_pass_claim_is_flagged_when_tests_missing() -> None:
    outputs = deepcopy(valid_llm_outputs())
    outputs["bucket_2"]["testing_performed"] = "All tests passed."  # type: ignore[index]

    issues = _issues(outputs)

    assert any(issue.code == "unsupported_test_claim" for issue in issues)


def test_unsupported_rollback_tested_claim_is_flagged() -> None:
    outputs = deepcopy(valid_llm_outputs())
    outputs["bucket_3"]["backout_plan"] = "Rollback tested successfully."  # type: ignore[index]

    issues = _issues(outputs)

    assert any(issue.code == "unsupported_rollback_claim" for issue in issues)


def test_absolute_no_risk_claim_is_flagged() -> None:
    outputs = deepcopy(valid_llm_outputs())
    outputs["bucket_3"]["risk_impact_analysis"] = "No risk."  # type: ignore[index]

    issues = _issues(outputs)

    assert any(issue.code == "absolute_risk_claim" for issue in issues)


def test_missing_pr_evidence_is_not_error() -> None:
    issues = _issues()
    pr_issues = [issue for issue in issues if issue.code == "missing_pr_evidence"]

    assert pr_issues
    assert all(issue.severity != "error" for issue in pr_issues)


def test_missing_test_evidence_is_warning() -> None:
    issues = _issues()

    assert any(
        issue.code == "missing_test_evidence"
        and issue.severity == "warning"
        for issue in issues
    )
