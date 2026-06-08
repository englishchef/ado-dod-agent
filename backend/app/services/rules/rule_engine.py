"""Phase 9 deterministic rule engine orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.app.models.rules import RuleEvaluation, RuleEvaluationSummary, RuleResult
from backend.app.services.rules.backout_rules import evaluate_backout_rules
from backend.app.services.rules.confidence_rules import calculate_confidence_adjustments
from backend.app.services.rules.field_quality_rules import evaluate_field_quality_rules
from backend.app.services.rules.post_generation_rules import evaluate_unsupported_claim_rules
from backend.app.services.rules.risk_rules import evaluate_risk_rules
from backend.app.services.rules.test_completeness import (
    calculate_test_completeness_score,
    evaluate_test_completeness_rules,
)

_SEVERITY_ORDER = {"info": 0, "warning": 1, "review": 2, "error": 3}


def evaluate_rules(
    build_id: int,
    evidence_bundle: dict[str, Any],
    service_now_payload: dict[str, Any],
    llm_outputs: dict[str, Any] | None = None,
    validated_output: dict[str, Any] | None = None,
    confidence: dict[str, Any] | None = None,
    routing_decisions: dict[str, Any] | None = None,
    traceability_report: dict[str, Any] | None = None,
    source_paths: dict[str, str] | None = None,
) -> RuleEvaluation:
    """Evaluate deterministic post-generation rules against existing artifacts."""

    safe_llm_outputs = llm_outputs or {}
    safe_confidence = confidence or {}
    score = calculate_test_completeness_score(
        evidence_bundle=evidence_bundle,
        service_now_payload=service_now_payload,
        validated_output=validated_output,
        routing_decisions=routing_decisions,
        traceability_report=traceability_report,
    )
    rules_triggered: list[RuleResult] = [
        *evaluate_test_completeness_rules(evidence_bundle, score, validated_output),
        *evaluate_unsupported_claim_rules(
            service_now_payload,
            evidence_bundle,
            traceability_report,
        ),
        *evaluate_backout_rules(service_now_payload, evidence_bundle, traceability_report),
        *evaluate_risk_rules(
            service_now_payload,
            evidence_bundle,
            routing_decisions,
            safe_confidence,
            score,
        ),
        *evaluate_field_quality_rules(service_now_payload, safe_llm_outputs),
    ]
    adjustments = calculate_confidence_adjustments(rules_triggered, safe_confidence, score)
    summary = _summary(rules_triggered)
    return RuleEvaluation(
        build_id=build_id,
        generated_at=datetime.now(UTC),
        test_completeness_score=score,
        rules_triggered=rules_triggered,
        confidence_adjustments=adjustments,
        summary=summary,
        source_paths=source_paths or {},
        notes=["Rule evaluation is deterministic and does not mutate service_now_payload.json."],
    )


def _summary(rules: list[RuleResult]) -> RuleEvaluationSummary:
    counts = {"info": 0, "warning": 0, "review": 0, "error": 0}
    for rule in rules:
        counts[rule.severity] += 1
    highest = "info"
    if rules:
        highest = max((rule.severity for rule in rules), key=lambda value: _SEVERITY_ORDER[value])
    recommended_status = _recommended_status(rules, highest)
    return RuleEvaluationSummary(
        highest_severity=highest,  # type: ignore[arg-type]
        recommended_status=recommended_status,  # type: ignore[arg-type]
        info_count=counts["info"],
        warning_count=counts["warning"],
        review_count=counts["review"],
        error_count=counts["error"],
        triggered_rule_count=len(rules),
    )


def _recommended_status(rules: list[RuleResult], highest: str) -> str:
    if any(rule.rule_id in {"FIELD_EMPTY", "FIELD_PLACEHOLDER"} for rule in rules):
        return "failed"
    if highest == "error":
        return "needs_review"
    if highest == "review":
        return "needs_review"
    if highest == "warning":
        return "completed_with_warnings"
    return "completed"
