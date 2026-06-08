"""Tests for confidence adjustment recommendations."""

from __future__ import annotations

from backend.app.models.rules import RuleResult, TestCompletenessScore
from backend.app.services.rules.confidence_rules import calculate_confidence_adjustments


def _score() -> TestCompletenessScore:
    return TestCompletenessScore(
        overall_score=0.3,
        functional_score=0.0,
        nonfunctional_score=0.0,
        coverage_score=0.0,
        security_score=0.0,
        deployment_validation_score=0.5,
        traceability_score=0.5,
    )


def _rule(rule_id: str) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="general",
        severity="warning",
        message=rule_id,
    )


def test_test_no_automated_results_reduces_bucket_2() -> None:
    adjustments = calculate_confidence_adjustments(
        [_rule("TEST_NO_AUTOMATED_RESULTS")],
        {"overall": 0.8},
        _score(),
    )

    assert any(item.target == "bucket_2" and item.adjustment == -0.15 for item in adjustments)


def test_backout_no_anchor_reduces_bucket_3() -> None:
    adjustments = calculate_confidence_adjustments(
        [_rule("BACKOUT_NO_ROLLBACK_ANCHOR")],
        {"overall": 0.8},
        _score(),
    )

    assert any(item.target == "bucket_3" and item.adjustment == -0.20 for item in adjustments)


def test_raw_reference_leakage_reduces_overall() -> None:
    adjustments = calculate_confidence_adjustments(
        [_rule("RAW_REFERENCE_LEAKAGE")],
        {"overall": 0.8},
        _score(),
    )

    assert any(item.target == "overall" and item.adjustment == -0.20 for item in adjustments)
