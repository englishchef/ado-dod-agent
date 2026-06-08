"""Tests for Phase 9 rule engine orchestration."""

from __future__ import annotations

from backend.app.services.rules.rule_engine import evaluate_rules


def _clean_payload() -> dict[str, str]:
    return {
        "change_description": "Deploy service update.",
        "short_change_description": "Deploy service update",
        "justification": "Improve supportability.",
        "testing_performed": "Automated tests passed: 10 total, 10 passed.",
        "implementation_plan": "Deploy through the approved release pipeline.",
        "validation_plan": "Validate API health and review monitoring logs.",
        "backout_plan": "Rollback by redeploying the previous known-good build if needed.",
        "risk_impact_analysis": "No specific risk signals were detected.",
    }


def _strong_evidence() -> dict[str, object]:
    return {
        "bucket_2": {
            "test_evidence": {"total_runs": 1, "total_tests": 10, "passed_tests": 10},
            "validation_signals": ["Smoke validation"],
            "quality_signals": [
                "security scan passed",
                "coverage report available",
                "load test completed",
            ],
            "artifact_evidence": [{"name": "drop"}],
            "task_evidence": [{"name": "Run performance validation", "result": "succeeded"}],
        },
        "bucket_3": {
            "risk_flags": {},
            "artifact_evidence": [{"name": "drop"}],
            "rollback_indicators": ["previous known-good build"],
        },
    }


def test_rule_engine_combines_rules_from_categories() -> None:
    evaluation = evaluate_rules(
        5,
        {"bucket_2": {"test_evidence": {"total_tests": 0}}, "bucket_3": {"risk_flags": {}}},
        {**_clean_payload(), "testing_performed": "All tests passed raw.changes.value[3]."},
    )

    rule_ids = {rule.rule_id for rule in evaluation.rules_triggered}
    assert "UNSUPPORTED_TEST_PASS_CLAIM" in rule_ids
    assert "RAW_REFERENCE_LEAKAGE" in rule_ids


def test_recommended_status_completed_when_no_rules() -> None:
    evaluation = evaluate_rules(
        5,
        _strong_evidence(),
        _clean_payload(),
        traceability_report={"field_traceability": {"x": {"friendly_refs": ["work_item:1"]}}},
    )

    assert evaluation.summary.recommended_status == "completed"


def test_recommended_status_completed_with_warnings() -> None:
    payload = {**_clean_payload(), "validation_plan": "Review."}
    evaluation = evaluate_rules(5, _strong_evidence(), payload)

    assert evaluation.summary.recommended_status == "completed_with_warnings"


def test_recommended_status_needs_review_with_review_rule() -> None:
    evaluation = evaluate_rules(5, {"bucket_2": {}, "bucket_3": {}}, _clean_payload())

    assert evaluation.summary.recommended_status == "needs_review"


def test_recommended_status_failed_only_for_unusable_payload() -> None:
    payload = {**_clean_payload(), "change_description": ""}
    evaluation = evaluate_rules(5, _strong_evidence(), payload)

    assert evaluation.summary.recommended_status == "failed"


def test_rule_evaluation_serializes() -> None:
    payload = evaluate_rules(5, _strong_evidence(), _clean_payload()).model_dump(mode="json")

    assert payload["build_id"] == 5
    assert "test_completeness_score" in payload
