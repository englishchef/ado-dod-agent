"""Tests for backout plan quality rules."""

from __future__ import annotations

from backend.app.services.rules.backout_rules import evaluate_backout_rules


def test_no_rollback_anchor_triggers_rule() -> None:
    rules = evaluate_backout_rules({"backout_plan": "Notify support if there is an issue."}, {})

    assert "BACKOUT_NO_ROLLBACK_ANCHOR" in {rule.rule_id for rule in rules}


def test_database_change_without_db_backout_triggers_rule() -> None:
    rules = evaluate_backout_rules(
        {"backout_plan": "Redeploy the previous application build."},
        {"bucket_3": {"risk_flags": {"database_change_detected": True}}},
    )

    assert "DB_CHANGE_NO_DB_BACKOUT" in {rule.rule_id for rule in rules}


def test_infra_change_without_infra_backout_triggers_rule() -> None:
    rules = evaluate_backout_rules(
        {"backout_plan": "Redeploy the previous application build."},
        {"bucket_3": {"risk_flags": {"infrastructure_change_detected": True}}},
    )

    assert "INFRA_CHANGE_NO_INFRA_BACKOUT" in {rule.rule_id for rule in rules}


def test_backout_refinement_validation_codes_flow_into_rule_evaluation() -> None:
    rules = evaluate_backout_rules(
        {"backout_plan": "Redeploy build 123 from the release pipeline."},
        {"bucket_3": {"uat_deployment": {"activities": []}}},
    )
    rule_ids = {rule.rule_id for rule in rules}

    assert "BACKOUT_PLAN_DELIVERY_METADATA_LEAKAGE" in rule_ids
    assert "BACKOUT_PLAN_MISSING_STEPS" in rule_ids
    assert "BACKOUT_PLAN_MISSING_DURATION" in rule_ids
