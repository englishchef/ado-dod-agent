"""Tests for unsupported generated-claim rules."""

from __future__ import annotations

from backend.app.services.rules.post_generation_rules import evaluate_unsupported_claim_rules


def _payload(**updates: str) -> dict[str, str]:
    payload = {
        "testing_performed": "Automated test results were not available.",
        "validation_plan": "Validate service health.",
        "backout_plan": "Redeploy previous build.",
        "risk_impact_analysis": "No specific risk signals were detected.",
    }
    payload.update(updates)
    return payload


def test_all_tests_passed_without_evidence_triggers_rule() -> None:
    rules = evaluate_unsupported_claim_rules(_payload(testing_performed="All tests passed."), {})

    assert {rule.rule_id for rule in rules} >= {
        "UNSUPPORTED_TEST_PASS_CLAIM",
        "UNSUPPORTED_ALL_TESTS_PASSED",
    }


def test_rollback_tested_claim_without_evidence_triggers_rule() -> None:
    rules = evaluate_unsupported_claim_rules(
        _payload(backout_plan="Rollback tested successfully."),
        {},
    )

    assert "UNSUPPORTED_ROLLBACK_TESTED" in {rule.rule_id for rule in rules}


def test_no_risk_claim_triggers_rule() -> None:
    rules = evaluate_unsupported_claim_rules(_payload(risk_impact_analysis="No risk."), {})

    assert "UNSUPPORTED_NO_RISK_CLAIM" in {rule.rule_id for rule in rules}


def test_raw_reference_in_payload_triggers_leakage_rule() -> None:
    rules = evaluate_unsupported_claim_rules(
        _payload(testing_performed="Reviewed raw.changes.value[3]."),
        {},
    )

    assert "RAW_REFERENCE_LEAKAGE" in {rule.rule_id for rule in rules}
