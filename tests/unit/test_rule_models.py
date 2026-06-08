"""Tests for Phase 9 rule models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from backend.app.models.rules import (
    RuleEvaluation,
    RuleEvaluationSummary,
    RuleResult,
    TestCompletenessScore,
)
from pydantic import ValidationError


def _score() -> TestCompletenessScore:
    return TestCompletenessScore(
        overall_score=0.5,
        functional_score=0.5,
        nonfunctional_score=0.5,
        coverage_score=0.5,
        security_score=0.5,
        deployment_validation_score=0.5,
        traceability_score=0.5,
        rationale=["partial"],
        missing_evidence=["coverage"],
    )


def test_rule_result_serializes() -> None:
    payload = RuleResult(
        rule_id="TEST_NO_AUTOMATED_RESULTS",
        category="test_completeness",
        severity="review",
        message="Missing tests.",
        evidence_refs=["pipeline_task:Run_Tests"],
    ).model_dump(mode="json")

    assert payload["severity"] == "review"
    assert payload["evidence_refs"] == ["pipeline_task:Run_Tests"]


def test_test_completeness_score_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        TestCompletenessScore(
            overall_score=1.2,
            functional_score=0.5,
            nonfunctional_score=0.5,
            coverage_score=0.5,
            security_score=0.5,
            deployment_validation_score=0.5,
            traceability_score=0.5,
        )


def test_rule_evaluation_serializes() -> None:
    payload = RuleEvaluation(
        build_id=5,
        generated_at=datetime(2026, 6, 1, tzinfo=UTC),
        test_completeness_score=_score(),
        rules_triggered=[],
        confidence_adjustments=[],
        summary=RuleEvaluationSummary(
            highest_severity="info",
            recommended_status="completed",
        ),
        source_paths={"service_now_payload": "payload.json"},
    ).model_dump(mode="json")

    assert payload["schema_version"] == "1.0"
    assert payload["source_paths"]["service_now_payload"] == "payload.json"
