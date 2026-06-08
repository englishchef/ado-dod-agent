"""Confidence adjustment recommendations from deterministic rules."""

from __future__ import annotations

from typing import Any

from backend.app.models.rules import ConfidenceAdjustment, RuleResult, TestCompletenessScore

_ADJUSTMENTS: dict[str, tuple[tuple[str, float], ...]] = {
    "TEST_NO_AUTOMATED_RESULTS": (("bucket_2", -0.15), ("overall", -0.05)),
    "TEST_FAILURES_PRESENT": (("bucket_2", -0.20), ("overall", -0.10)),
    "TEST_STAGE_SKIPPED": (("bucket_2", -0.15),),
    "UNSUPPORTED_TEST_PASS_CLAIM": (("bucket_2", -0.20), ("overall", -0.10)),
    "UNSUPPORTED_ALL_TESTS_PASSED": (("bucket_2", -0.20), ("overall", -0.10)),
    "UNSUPPORTED_ROLLBACK_TESTED": (("bucket_3", -0.20), ("overall", -0.10)),
    "BACKOUT_NO_ROLLBACK_ANCHOR": (("bucket_3", -0.20),),
    "DB_CHANGE_NO_DB_BACKOUT": (("bucket_3", -0.15),),
    "DB_CHANGE_RISK_MISSING": (("bucket_3", -0.15),),
    "RAW_REFERENCE_LEAKAGE": (("overall", -0.20),),
    "FIELD_EMPTY": (("overall", -0.30),),
    "FIELD_PLACEHOLDER": (("overall", -0.30),),
}


def calculate_confidence_adjustments(
    rules_triggered: list[RuleResult],
    confidence: dict[str, Any],
    test_completeness_score: TestCompletenessScore,
) -> list[ConfidenceAdjustment]:
    """Return confidence adjustment recommendations without mutating confidence.json."""

    _ = confidence, test_completeness_score
    adjustments: list[ConfidenceAdjustment] = []
    for rule in rules_triggered:
        for target, adjustment in _ADJUSTMENTS.get(rule.rule_id, ()):
            adjustments.append(
                ConfidenceAdjustment(
                    target=target,  # type: ignore[arg-type]
                    adjustment=adjustment,
                    reason=rule.message,
                    rule_id=rule.rule_id,
                )
            )
    return adjustments
