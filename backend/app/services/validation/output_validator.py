"""Deterministic validators for generated DoD ServiceNow payloads."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import ValidationError

from backend.app.models.llm_outputs import CombinedLlmOutputs
from backend.app.models.validated_outputs import (
    PLACEHOLDER_VALUES,
    BucketValidationResult,
    ServiceNowPayload,
    ValidationIssue,
)
from backend.app.services.validation.output_repair import (
    detect_delivery_detail_leakage,
    longest_contiguous_word_overlap,
    normalized_words,
    sequence_similarity,
)

Severity = Literal["info", "warning", "error"]

BUCKET_FIELDS = {
    "bucket_1": ("change_description", "short_change_description", "justification"),
    "bucket_2": ("testing_performed", "implementation_plan", "validation_plan"),
    "bucket_3": ("backout_plan", "risk_impact_analysis"),
}

_RAW_REFERENCE_LEAKAGE_RE = re.compile(
    r"(\[(?:raw|canonical|evidence)\.[^\]]+\]|"
    r"\b(?:raw|canonical|evidence)\.[A-Za-z0-9_.-]+(?:\[[0-9]+\])*|"
    r"\bsource_ref(?:_map)?\b)",
    re.IGNORECASE,
)
_CHANGE_ENUMERATION_RE = re.compile(
    r"\b(?:add|adds|change|changes|correct|corrects|enhance|enhances|fix|fixes|"
    r"implement|implements|introduce|introduces|modify|modifies|resolve|resolves|"
    r"support|supports|update|updates)\b",
    re.IGNORECASE,
)
_RATIONALE_RE = re.compile(
    r"\b(?:because|benefit|compliance|correctness|efficiency|ensure|necessary|prevent|"
    r"reduce|reliability|required|risk|supportability)\b|user experience|"
    r"operational consistency",
    re.IGNORECASE,
)


def validate_llm_outputs(
    llm_outputs: CombinedLlmOutputs | dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
) -> list[BucketValidationResult]:
    """Validate each generated bucket output without repairing or regenerating content."""

    payload = _as_dict(llm_outputs)
    evidence = evidence_bundle or {}
    results: list[BucketValidationResult] = []
    for bucket_name, required_fields in BUCKET_FIELDS.items():
        bucket_payload = payload.get(bucket_name)
        issues: list[ValidationIssue] = []
        if not isinstance(bucket_payload, dict):
            issues.append(
                _issue(
                    "error",
                    "missing_bucket",
                    "Required bucket output is missing.",
                    None,
                    bucket_name,
                )
            )
            results.append(
                BucketValidationResult(bucket_name=bucket_name, is_valid=False, issues=issues)
            )
            continue

        for field in required_fields:
            _validate_text_field(bucket_payload.get(field), field, bucket_name, issues)

        evidence_used = bucket_payload.get("evidence_used")
        if not isinstance(evidence_used, list) or len(evidence_used) == 0:
            issues.append(
                _issue(
                    "warning",
                    "missing_evidence_used",
                    "Bucket output does not include evidence_used references.",
                    "evidence_used",
                    bucket_name,
                )
            )

        issues.extend(_unsupported_claim_issues(bucket_name, bucket_payload, evidence))
        if bucket_name == "bucket_1":
            issues.extend(validate_change_intent_field_separation(bucket_payload, bucket_name))
        issues.extend(_missing_context_issues(bucket_name, evidence))
        results.append(
            BucketValidationResult(
                bucket_name=bucket_name,
                is_valid=not any(issue.severity == "error" for issue in issues),
                issues=issues,
            )
        )
    return results


def detect_raw_reference_leakage(text: str) -> bool:
    """Return whether text contains raw/internal evidence references."""

    return bool(_RAW_REFERENCE_LEAKAGE_RE.search(text))


def validate_no_raw_reference_leakage(
    payload: ServiceNowPayload | dict[str, Any],
) -> list[ValidationIssue]:
    """Validate that final ServiceNow fields do not expose internal evidence refs."""

    payload_dict = payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
    issues: list[ValidationIssue] = []
    for field, value in payload_dict.items():
        if isinstance(value, str) and detect_raw_reference_leakage(value):
            issues.append(
                _issue(
                    "error",
                    "RAW_REFERENCE_LEAKAGE",
                    "Final ServiceNow field contains internal evidence reference.",
                    field,
                    None,
                )
            )
    return issues


def validate_change_intent_field_separation(
    payload: ServiceNowPayload | dict[str, Any],
    bucket: str | None = None,
) -> list[ValidationIssue]:
    """Validate that description and justification serve distinct field purposes."""

    payload_dict = payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
    change_description = payload_dict.get("change_description")
    justification = payload_dict.get("justification")
    issues: list[ValidationIssue] = []

    if isinstance(change_description, str) and detect_delivery_detail_leakage(
        change_description
    ):
        issues.append(
            _issue(
                "warning",
                "CHANGE_DESCRIPTION_DELIVERY_DETAIL_LEAKAGE",
                "Change description contains build, source-control, or delivery metadata.",
                "change_description",
                bucket,
            )
        )
    if isinstance(justification, str) and detect_delivery_detail_leakage(justification):
        issues.append(
            _issue(
                "warning",
                "JUSTIFICATION_DELIVERY_DETAIL_LEAKAGE",
                "Justification contains build, source-control, or delivery metadata.",
                "justification",
                bucket,
            )
        )
    if not isinstance(change_description, str) or not isinstance(justification, str):
        return issues

    description_words = normalized_words(change_description)
    justification_words = normalized_words(justification)
    shorter_word_count = min(len(description_words), len(justification_words))
    similarity = sequence_similarity(change_description, justification)
    longest_overlap = longest_contiguous_word_overlap(change_description, justification)
    if shorter_word_count >= 18 and similarity >= 0.88:
        issues.append(
            _issue(
                "warning",
                "JUSTIFICATION_REPETITIVE",
                "Justification is nearly identical to change description.",
                "justification",
                bucket,
            )
        )

    overlap_reasons: list[str] = []
    if longest_overlap >= 15:
        overlap_reasons.append("copies a long contiguous phrase from change description")
    if (
        len(description_words) >= 50
        and len(justification_words) >= 90
        and len(justification_words) > len(description_words) * 1.25
    ):
        overlap_reasons.append("is substantially longer than change description")
    change_terms = len(_CHANGE_ENUMERATION_RE.findall(justification))
    rationale_terms = len(_RATIONALE_RE.findall(justification))
    if change_terms >= 4 and rationale_terms <= 1:
        overlap_reasons.append("primarily enumerates changes instead of explaining rationale")
    if overlap_reasons:
        issues.append(
            _issue(
                "warning",
                "FIELD_PURPOSE_OVERLAP",
                "Justification " + "; ".join(overlap_reasons) + ".",
                "justification",
                bucket,
            )
        )
    return issues


def validate_service_now_payload(
    payload: ServiceNowPayload | dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
) -> list[ValidationIssue]:
    """Validate the final flat ServiceNow payload."""

    evidence = evidence_bundle or {}
    issues: list[ValidationIssue] = []
    payload_model: ServiceNowPayload | None = None
    try:
        payload_model = ServiceNowPayload.model_validate(
            payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
        )
    except ValidationError as exc:
        for error in exc.errors():
            field = str(error.get("loc", ["unknown"])[0])
            issues.append(
                _issue("error", "invalid_service_now_field", str(error["msg"]), field, None)
            )

    payload_dict = (
        payload_model.model_dump()
        if payload_model is not None
        else payload.model_dump()
        if isinstance(payload, ServiceNowPayload)
        else payload
    )
    issues.extend(validate_no_raw_reference_leakage(payload_dict))
    issues.extend(validate_change_intent_field_separation(payload_dict))
    joined_payload = " ".join(str(value) for value in payload_dict.values())
    issues.extend(_risk_claim_issues(joined_payload, None, "risk_impact_analysis"))
    if _tests_missing(evidence):
        issues.extend(_test_claim_issues(joined_payload, None, "testing_performed"))
    if not _rollback_validation_supported(evidence):
        issues.extend(_rollback_claim_issues(joined_payload, None, "backout_plan"))
    return issues


def _as_dict(llm_outputs: CombinedLlmOutputs | dict[str, Any]) -> dict[str, Any]:
    if isinstance(llm_outputs, CombinedLlmOutputs):
        return llm_outputs.model_dump(mode="json")
    return llm_outputs


def _validate_text_field(
    value: Any,
    field: str,
    bucket: str,
    issues: list[ValidationIssue],
) -> None:
    if value is None:
        issues.append(
            _issue("error", "missing_required_field", "Required field is missing.", field, bucket)
        )
        return
    if not isinstance(value, str) or value.strip() == "":
        issues.append(
            _issue("error", "empty_required_field", "Required field is empty.", field, bucket)
        )
        return
    if value.strip().lower() in PLACEHOLDER_VALUES:
        issues.append(
            _issue("error", "placeholder_field", "Field contains placeholder text.", field, bucket)
        )


def _unsupported_claim_issues(
    bucket_name: str,
    bucket_payload: dict[str, Any],
    evidence_bundle: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field, text in bucket_payload.items():
        if not isinstance(text, str):
            continue
        if _tests_missing(evidence_bundle):
            issues.extend(_test_claim_issues(text, bucket_name, field))
        if not _rollback_validation_supported(evidence_bundle):
            issues.extend(_rollback_claim_issues(text, bucket_name, field))
        issues.extend(_risk_claim_issues(text, bucket_name, field))
    return issues


def _missing_context_issues(
    bucket_name: str,
    evidence_bundle: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if bucket_name == "bucket_1":
        bucket = _bucket(evidence_bundle, "bucket_1")
        if not bucket.get("pull_request_evidence"):
            issues.append(
                _issue(
                    "info",
                    "missing_pr_evidence",
                    "Pull request evidence is missing.",
                    None,
                    bucket_name,
                )
            )
        if not bucket.get("work_item_evidence"):
            issues.append(
                _issue(
                    "warning",
                    "missing_work_item_evidence",
                    "Work item evidence is missing.",
                    None,
                    bucket_name,
                )
            )
    if bucket_name == "bucket_2" and _tests_missing(evidence_bundle):
        issues.append(
            _issue(
                "warning",
                "missing_test_evidence",
                "Test result evidence is missing.",
                None,
                bucket_name,
            )
        )
    bucket_3 = _bucket(evidence_bundle, "bucket_3")
    if bucket_name == "bucket_3" and not bucket_3.get("artifact_evidence"):
        issues.append(
            _issue(
                "warning",
                "missing_artifact_evidence",
                "Artifact evidence is missing.",
                None,
                bucket_name,
            )
        )
    return issues


def _test_claim_issues(
    text: str,
    bucket: str | None,
    field: str | None,
) -> list[ValidationIssue]:
    phrases = (
        "tests passed",
        "all tests passed",
        "automated tests passed",
        "functional tests passed",
        "regression tests passed",
    )
    if any(phrase in text.lower() for phrase in phrases):
        return [
            _issue(
                "warning",
                "unsupported_test_claim",
                "Test pass claim is not supported by collected test evidence.",
                field,
                bucket,
            )
        ]
    return []


def _rollback_claim_issues(
    text: str,
    bucket: str | None,
    field: str | None,
) -> list[ValidationIssue]:
    phrases = ("rollback tested", "backout tested", "rollback validated")
    if any(phrase in text.lower() for phrase in phrases):
        return [
            _issue(
                "warning",
                "unsupported_rollback_claim",
                "Rollback validation claim is not supported by collected evidence.",
                field,
                bucket,
            )
        ]
    return []


def _risk_claim_issues(
    text: str,
    bucket: str | None,
    field: str | None,
) -> list[ValidationIssue]:
    phrases = ("no risk", "no impact", "zero risk")
    if any(phrase in text.lower() for phrase in phrases):
        return [
            _issue(
                "warning",
                "absolute_risk_claim",
                "Absolute no-risk/no-impact claim should be qualified by collected evidence.",
                field,
                bucket,
            )
        ]
    return []


def _tests_missing(evidence_bundle: dict[str, Any]) -> bool:
    test_evidence = _bucket(evidence_bundle, "bucket_2").get("test_evidence")
    if not isinstance(test_evidence, dict):
        return True
    missing_context = test_evidence.get("missing_test_context") or []
    total_tests = test_evidence.get("total_tests")
    return bool(missing_context) or total_tests in (None, 0)


def _rollback_validation_supported(evidence_bundle: dict[str, Any]) -> bool:
    bucket_3 = _bucket(evidence_bundle, "bucket_3")
    indicators = " ".join(
        str(item).lower() for item in bucket_3.get("rollback_indicators", [])
    )
    signals = " ".join(str(item).lower() for item in bucket_3.get("risk_signals", []))
    supported_terms = ("rollback tested", "rollback validated", "backout tested")
    return any(term in f"{indicators} {signals}" for term in supported_terms)


def _bucket(evidence_bundle: dict[str, Any], name: str) -> dict[str, Any]:
    payload = evidence_bundle.get(name)
    return payload if isinstance(payload, dict) else {}


def _issue(
    severity: Severity,
    code: str,
    message: str,
    field: str | None,
    bucket: str | None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        code=code,
        message=message,
        field=field,
        bucket=bucket,
    )
