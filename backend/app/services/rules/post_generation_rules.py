"""Rules for unsupported claims in generated ServiceNow field text."""

from __future__ import annotations

from typing import Any

from backend.app.models.rules import RuleResult
from backend.app.services.rules.test_completeness import (
    has_failed_tests,
    has_test_results,
)
from backend.app.services.validation.output_validator import detect_raw_reference_leakage


def evaluate_unsupported_claim_rules(
    service_now_payload: dict[str, Any],
    evidence_bundle: dict[str, Any],
    traceability_report: dict[str, Any] | None = None,
) -> list[RuleResult]:
    """Evaluate unsupported AI-generated claim rules."""

    _ = traceability_report
    rules: list[RuleResult] = []
    testing_text = _field_text(service_now_payload, "testing_performed")
    validation_text = _field_text(service_now_payload, "validation_plan")
    risk_text = _field_text(service_now_payload, "risk_impact_analysis")
    backout_text = _field_text(service_now_payload, "backout_plan")
    all_text = " ".join(str(value) for value in service_now_payload.values()).lower()

    test_claim_text = f"{testing_text} {validation_text}"
    test_pass_phrases = (
        "tests passed",
        "automated tests passed",
        "functional tests passed",
        "regression tests passed",
    )
    if _contains_any(test_claim_text, test_pass_phrases) and not has_test_results(
        evidence_bundle
    ):
        rules.append(
            _rule(
                "UNSUPPORTED_TEST_PASS_CLAIM",
                "review",
                "Generated text claims tests passed without supporting test evidence.",
                "testing_performed",
            )
        )
    if "all tests passed" in test_claim_text and (
        not has_test_results(evidence_bundle) or has_failed_tests(evidence_bundle)
    ):
        rules.append(
            _rule(
                "UNSUPPORTED_ALL_TESTS_PASSED",
                "review",
                "Generated text claims all tests passed without complete passing evidence.",
                "testing_performed",
            )
        )
    rollback_claim_phrases = (
        "rollback tested",
        "backout tested",
        "rollback validated",
        "rollback proven",
    )
    if _contains_any(backout_text, rollback_claim_phrases) and not _rollback_supported(
        evidence_bundle
    ):
        rules.append(
            _rule(
                "UNSUPPORTED_ROLLBACK_TESTED",
                "review",
                "Generated text claims rollback validation without supporting evidence.",
                "backout_plan",
            )
        )
    approval_phrases = (
        "qa approval",
        "business approval",
        "explicit signoff",
        "signed off",
        "approved by qa",
    )
    if _contains_any(all_text, approval_phrases) and not _approval_supported(evidence_bundle):
        rules.append(
            _rule(
                "UNSUPPORTED_QA_APPROVAL",
                "review",
                "Generated text claims approval or signoff without approval evidence.",
            )
        )
    no_risk_claim = _contains_any(risk_text, ("no risk", "zero risk", "risk-free"))
    if no_risk_claim and "no specific risk signals" not in risk_text:
        rules.append(
            _rule(
                "UNSUPPORTED_NO_RISK_CLAIM",
                "review",
                "Generated text uses absolute no-risk language.",
                "risk_impact_analysis",
            )
        )
    if _contains_any(risk_text, ("no impact", "zero impact")) and "no specific" not in risk_text:
        rules.append(
            _rule(
                "UNSUPPORTED_NO_IMPACT_CLAIM",
                "review",
                "Generated text uses absolute no-impact language.",
                "risk_impact_analysis",
            )
        )
    for field, value in service_now_payload.items():
        if isinstance(value, str) and detect_raw_reference_leakage(value):
            rules.append(
                _rule(
                    "RAW_REFERENCE_LEAKAGE",
                    "error",
                    "Final field contains an internal evidence reference.",
                    field,
                )
            )
    return rules


def _rule(
    rule_id: str,
    severity: str,
    message: str,
    field_name: str | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="unsupported_claim",
        severity=severity,  # type: ignore[arg-type]
        message=message,
        field_name=field_name,
    )


def _field_text(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    return value.lower() if isinstance(value, str) else ""


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _rollback_supported(evidence_bundle: dict[str, Any]) -> bool:
    text = str(evidence_bundle).lower()
    return any(term in text for term in ("rollback tested", "rollback validated", "backout tested"))


def _approval_supported(evidence_bundle: dict[str, Any]) -> bool:
    text = str(evidence_bundle).lower()
    return any(term in text for term in ("approval", "approved", "signoff", "signed off"))
