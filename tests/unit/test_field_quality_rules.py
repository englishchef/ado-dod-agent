"""Tests for ServiceNow field quality rules."""

from __future__ import annotations

from backend.app.services.rules.field_quality_rules import evaluate_field_quality_rules


def _payload(**updates: str) -> dict[str, str]:
    payload = {
        "change_description": "Deploy service update.",
        "short_change_description": "Deploy service update",
        "justification": "Improve supportability.",
        "testing_performed": "Pipeline validation was reviewed.",
        "implementation_plan": "Deploy through the approved release pipeline.",
        "validation_plan": "Validate API health and review monitoring logs.",
        "backout_plan": "Redeploy previous build.",
        "risk_impact_analysis": "No specific risk signals were detected.",
    }
    payload.update(updates)
    return payload


def _ids(payload: dict[str, str]) -> set[str]:
    return {rule.rule_id for rule in evaluate_field_quality_rules(payload)}


def test_empty_field_triggers_rule() -> None:
    assert "FIELD_EMPTY" in _ids(_payload(change_description=""))


def test_placeholder_triggers_rule() -> None:
    assert "FIELD_PLACEHOLDER" in _ids(_payload(justification="TBD"))


def test_long_short_description_triggers_rule() -> None:
    assert "SHORT_DESCRIPTION_TOO_LONG" in _ids(
        _payload(short_change_description="x" * 200)
    )


def test_generic_validation_plan_triggers_rule() -> None:
    assert "VALIDATION_PLAN_TOO_GENERIC" in _ids(_payload(validation_plan="Review."))


def test_markdown_triggers_rule() -> None:
    assert "MARKDOWN_IN_FIELD" in _ids(_payload(change_description="```text\nDeploy\n```"))


def test_duplicate_content_triggers_rule() -> None:
    assert "DUPLICATE_FIELD_CONTENT" in _ids(
        _payload(justification="Deploy service update.")
    )
