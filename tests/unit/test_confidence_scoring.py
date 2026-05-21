"""Tests for Phase 6 confidence scoring."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime

from backend.app.models.validated_outputs import ValidationIssue
from backend.app.services.scoring.confidence import score_confidence


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


def test_score_decreases_when_test_results_are_missing() -> None:
    score = score_confidence(valid_llm_outputs(), evidence_bundle(), [])

    assert score.bucket_2 < 0.8


def test_score_decreases_when_evidence_used_is_empty() -> None:
    outputs = deepcopy(valid_llm_outputs())
    outputs["bucket_1"]["evidence_used"] = []  # type: ignore[index]

    score = score_confidence(outputs, evidence_bundle(), [])

    assert score.bucket_1 < 0.8


def test_score_increases_when_work_items_commits_artifacts_exist() -> None:
    evidence = deepcopy(evidence_bundle())
    evidence["bucket_1"]["work_item_evidence"] = [{"id": 1}]  # type: ignore[index]

    score = score_confidence(valid_llm_outputs(), evidence, [])

    assert score.bucket_1 > 0.65


def test_score_is_blended_with_model_confidence() -> None:
    outputs = deepcopy(valid_llm_outputs())
    outputs["bucket_1"]["model_confidence"] = 0.1  # type: ignore[index]

    score = score_confidence(outputs, evidence_bundle(), [])

    assert score.bucket_1 < 0.7


def test_overall_score_is_average_of_buckets_without_errors() -> None:
    score = score_confidence(valid_llm_outputs(), evidence_bundle(), [])
    expected = (score.bucket_1 + score.bucket_2 + score.bucket_3) / 3

    assert abs(score.overall - expected) < 0.000001


def test_rationale_contains_meaningful_messages() -> None:
    issue = ValidationIssue(
        severity="warning",
        code="missing_test_evidence",
        message="missing",
        bucket="bucket_2",
    )
    score = score_confidence(valid_llm_outputs(), evidence_bundle(), [issue])

    assert score.rationale["bucket_2"]
    assert any("warning" in text.lower() for text in score.rationale["bucket_2"])
