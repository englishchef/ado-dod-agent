"""ServiceNow field quality and style rules."""

from __future__ import annotations

from itertools import combinations
from typing import Any

from backend.app.models.rules import RuleResult
from backend.app.models.validated_outputs import PLACEHOLDER_VALUES
from backend.app.utils.config import get_settings

SERVICE_NOW_FIELDS = (
    "change_description",
    "short_change_description",
    "justification",
    "testing_performed",
    "implementation_plan",
    "validation_plan",
    "backout_plan",
    "risk_impact_analysis",
)
_IMPLEMENTATION_TERMS = (
    "deploy",
    "pipeline",
    "build",
    "release",
    "artifact",
    "environment",
    "stage",
    "rollback",
    "promote",
    "approve",
)
_VALIDATION_TERMS = (
    "validate",
    "smoke",
    "health",
    "monitoring",
    "logs",
    "dashboard",
    "api",
    "service check",
    "synthetic",
    "business validation",
)


def evaluate_field_quality_rules(
    service_now_payload: dict[str, Any],
    llm_outputs: dict[str, Any] | None = None,
    short_description_max_length: int | None = None,
) -> list[RuleResult]:
    """Evaluate deterministic field quality and style rules."""

    max_length = short_description_max_length or get_settings().DOD_SHORT_DESCRIPTION_MAX_LENGTH
    rules: list[RuleResult] = []
    for field in SERVICE_NOW_FIELDS:
        value = service_now_payload.get(field)
        text = value.strip() if isinstance(value, str) else ""
        if not text:
            rules.append(
                _rule("FIELD_EMPTY", "error", "Required ServiceNow field is empty.", field)
            )
            continue
        if text.lower() in PLACEHOLDER_VALUES:
            rules.append(
                _rule(
                    "FIELD_PLACEHOLDER",
                    "error",
                    "Required ServiceNow field contains placeholder text.",
                    field,
                )
            )
        if "```" in text or text.startswith("#"):
            rules.append(
                _rule(
                    "MARKDOWN_IN_FIELD",
                    "warning",
                    "ServiceNow field contains markdown artifacts.",
                    field,
                )
            )

    short_description = str(service_now_payload.get("short_change_description") or "")
    if len(short_description) > max_length:
        rules.append(
            _rule(
                "SHORT_DESCRIPTION_TOO_LONG",
                "warning",
                "Short description exceeds configured ServiceNow length.",
                "short_change_description",
                {"max_length": max_length, "actual_length": len(short_description)},
            )
        )

    implementation = str(service_now_payload.get("implementation_plan") or "").lower()
    if implementation and not any(term in implementation for term in _IMPLEMENTATION_TERMS):
        rules.append(
            _rule(
                "IMPLEMENTATION_PLAN_TOO_GENERIC",
                "warning",
                "Implementation plan lacks deployment sequence indicators.",
                "implementation_plan",
            )
        )
    validation = str(service_now_payload.get("validation_plan") or "").lower()
    if validation and not any(term in validation for term in _VALIDATION_TERMS):
        rules.append(
            _rule(
                "VALIDATION_PLAN_TOO_GENERIC",
                "warning",
                "Validation plan lacks post-deployment verification indicators.",
                "validation_plan",
            )
        )

    for first, second in combinations(SERVICE_NOW_FIELDS, 2):
        first_text = _normalized(service_now_payload.get(first))
        second_text = _normalized(service_now_payload.get(second))
        if first_text and first_text == second_text:
            rules.append(
                _rule(
                    "DUPLICATE_FIELD_CONTENT",
                    "warning",
                    f"{first} and {second} contain near-identical content.",
                    first,
                    {"duplicate_field": second},
                )
            )
            break

    rules.extend(_evidence_used_rules(llm_outputs))
    return rules


def _evidence_used_rules(llm_outputs: dict[str, Any] | None) -> list[RuleResult]:
    if not isinstance(llm_outputs, dict):
        return []
    rules: list[RuleResult] = []
    for bucket_name in ("bucket_1", "bucket_2", "bucket_3"):
        bucket = llm_outputs.get(bucket_name)
        if isinstance(bucket, dict) and not bucket.get("evidence_used"):
            rules.append(
                RuleResult(
                    rule_id="EVIDENCE_USED_EMPTY",
                    category="traceability",
                    severity="warning",
                    message="Bucket output does not include evidence_used references.",
                    bucket=bucket_name,
                )
            )
    return rules


def _rule(
    rule_id: str,
    severity: str,
    message: str,
    field_name: str,
    metadata: dict[str, Any] | None = None,
) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="field_quality",
        severity=severity,  # type: ignore[arg-type]
        message=message,
        field_name=field_name,
        metadata=metadata or {},
    )


def _normalized(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.lower().split())
