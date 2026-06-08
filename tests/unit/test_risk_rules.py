"""Tests for risk and impact consistency rules."""

from __future__ import annotations

from backend.app.services.rules.risk_rules import evaluate_risk_rules


def _evidence(flag: str) -> dict[str, object]:
    return {"bucket_3": {"risk_flags": {flag: True}}}


def test_db_risk_flag_without_db_mention_triggers_rule() -> None:
    rules = evaluate_risk_rules(
        {"risk_impact_analysis": "Service impact is limited."},
        _evidence("database_change_detected"),
    )

    assert "DB_CHANGE_RISK_MISSING" in {rule.rule_id for rule in rules}


def test_infra_risk_flag_without_infra_mention_triggers_rule() -> None:
    rules = evaluate_risk_rules(
        {"risk_impact_analysis": "Service impact is limited."},
        _evidence("infrastructure_change_detected"),
    )

    assert "INFRA_CHANGE_RISK_MISSING" in {rule.rule_id for rule in rules}


def test_dependency_risk_flag_without_dependency_mention_triggers_rule() -> None:
    rules = evaluate_risk_rules(
        {"risk_impact_analysis": "Service impact is limited."},
        _evidence("dependency_change_detected"),
    )

    assert "DEPENDENCY_RISK_MISSING" in {rule.rule_id for rule in rules}


def test_config_risk_flag_without_config_mention_triggers_rule() -> None:
    rules = evaluate_risk_rules(
        {"risk_impact_analysis": "Service impact is limited."},
        _evidence("config_change_detected"),
    )

    assert "CONFIG_RISK_MISSING" in {rule.rule_id for rule in rules}
