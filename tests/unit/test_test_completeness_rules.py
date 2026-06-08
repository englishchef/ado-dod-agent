"""Tests for Phase 9 test completeness scoring and rules."""

from __future__ import annotations

from backend.app.services.rules.test_completeness import (
    calculate_test_completeness_score,
    evaluate_test_completeness_rules,
)


def _empty_evidence() -> dict[str, object]:
    return {
        "bucket_2": {
            "test_evidence": {"total_runs": 0, "total_tests": 0, "failed_tests": 0},
            "task_evidence": [],
            "validation_signals": [],
            "quality_signals": [],
        },
        "bucket_3": {"failed_or_warning_evidence": [], "artifact_evidence": []},
    }


def _rules(evidence: dict[str, object]) -> set[str]:
    score = calculate_test_completeness_score(evidence, {})
    return {rule.rule_id for rule in evaluate_test_completeness_rules(evidence, score)}


def test_no_test_evidence_triggers_no_automated_results() -> None:
    assert "TEST_NO_AUTOMATED_RESULTS" in _rules(_empty_evidence())


def test_skipped_test_stage_triggers_rule() -> None:
    evidence = _empty_evidence()
    evidence["bucket_2"]["task_evidence"] = [  # type: ignore[index]
        {"name": "Run functional tests", "result": "skipped"}
    ]

    assert "TEST_STAGE_SKIPPED" in _rules(evidence)


def test_failed_tests_trigger_rule() -> None:
    evidence = _empty_evidence()
    evidence["bucket_2"]["test_evidence"] = {"total_tests": 10, "failed_tests": 1}  # type: ignore[index]

    assert "TEST_FAILURES_PRESENT" in _rules(evidence)


def test_missing_nonfunctional_evidence_triggers_rule() -> None:
    assert "NO_NONFUNCTIONAL_TEST_EVIDENCE" in _rules(_empty_evidence())


def test_score_is_low_when_no_test_or_validation_evidence_exists() -> None:
    score = calculate_test_completeness_score(_empty_evidence(), {})

    assert score.overall_score <= 0.30


def test_score_is_medium_when_tests_missing_but_validation_exists() -> None:
    evidence = _empty_evidence()
    evidence["bucket_2"]["validation_signals"] = ["Smoke validation completed"]  # type: ignore[index]
    evidence["bucket_2"]["artifact_evidence"] = [{"name": "drop"}]  # type: ignore[index]

    score = calculate_test_completeness_score(evidence, {})

    assert 0.25 < score.overall_score <= 0.60
