"""Risk tier assessment for Phase 7B routing."""

from __future__ import annotations

from typing import Any

from backend.app.models.routing import RiskTierAssessment

_HIGH_RISK_SIGNAL_TERMS = ("high risk", "critical", "production outage", "data loss", "security")


def assess_risk_tier(evidence_bundle: dict[str, Any]) -> RiskTierAssessment:
    """Assess conservative risk tier from rollback/risk evidence."""

    bucket_2 = _as_dict(evidence_bundle.get("bucket_2"))
    bucket_3 = _as_dict(evidence_bundle.get("bucket_3"))
    test_evidence = _as_dict(bucket_2.get("test_evidence"))
    risk_flags = _bool_dict(_as_dict(bucket_3.get("risk_flags")))
    risk_signals = [str(item) for item in _as_list(bucket_3.get("risk_signals"))]
    missing_context = _collect_missing_context(bucket_2, bucket_3)
    failed_or_warning = _as_list(bucket_3.get("failed_or_warning_evidence"))
    artifacts = _as_list(bucket_3.get("artifact_evidence"))
    service_context = _as_dict(bucket_3.get("service_context"))
    source_version = _as_str(service_context.get("source_version"))

    reasons: list[str] = []
    high_conditions = [
        ("database_change_detected", "Database change evidence was detected."),
        ("infrastructure_change_detected", "Infrastructure change evidence was detected."),
    ]
    for flag, reason in high_conditions:
        if risk_flags.get(flag):
            reasons.append(reason)

    failed_tests = _as_int(test_evidence.get("failed_tests")) or 0
    if failed_tests > 0:
        reasons.append(f"Failed test evidence is present: failed_tests={failed_tests}.")
    if _has_failed_timeline_evidence(failed_or_warning):
        reasons.append("Failed timeline/deployment evidence is present.")
    if _has_high_risk_signal(risk_signals):
        reasons.append("An explicit high-risk signal appears in risk evidence.")
    if reasons:
        return RiskTierAssessment(
            risk_tier="high",
            reasons=reasons,
            risk_flags=risk_flags,
            missing_context=missing_context,
        )

    medium_reasons: list[str] = []
    for flag, reason in (
        ("dependency_change_detected", "Dependency change evidence was detected."),
        ("config_change_detected", "Configuration change evidence was detected."),
        ("feature_flag_change_detected", "Feature flag change evidence was detected."),
    ):
        if risk_flags.get(flag):
            medium_reasons.append(reason)
    if _has_missing_test_evidence(test_evidence):
        medium_reasons.append("Test evidence is missing or incomplete.")
    if not artifacts:
        medium_reasons.append("Artifact evidence is missing.")
    if _has_validation_warnings(failed_or_warning):
        medium_reasons.append("Validation warning evidence is present.")
    if medium_reasons:
        return RiskTierAssessment(
            risk_tier="medium",
            reasons=medium_reasons,
            risk_flags=risk_flags,
            missing_context=missing_context,
        )

    low_reasons = [
        "No configured major risk flag was detected in the evidence.",
        "No failed or warning evidence was detected.",
    ]
    if artifacts:
        low_reasons.append("Artifact evidence is available.")
    if source_version:
        low_reasons.append("Source version is available.")
    return RiskTierAssessment(
        risk_tier="low",
        reasons=low_reasons,
        risk_flags=risk_flags,
        missing_context=missing_context,
    )


def _collect_missing_context(bucket_2: dict[str, Any], bucket_3: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    test_evidence = _as_dict(bucket_2.get("test_evidence"))
    missing.extend(str(item) for item in _as_list(test_evidence.get("missing_test_context")))
    missing.extend(str(item) for item in _as_list(bucket_3.get("evidence_gaps")))
    return _dedupe(missing)


def _has_missing_test_evidence(test_evidence: dict[str, Any]) -> bool:
    total_tests = _as_int(test_evidence.get("total_tests")) or 0
    missing_test_context = _as_list(test_evidence.get("missing_test_context"))
    return total_tests == 0 or bool(missing_test_context)


def _has_failed_timeline_evidence(items: list[Any]) -> bool:
    for item in items:
        payload = _as_dict(item)
        source_type = (_as_str(payload.get("source_type")) or "").lower()
        result = (_as_str(payload.get("result")) or "").lower()
        if "timeline" in source_type and result and result not in {"succeeded", "warning"}:
            return True
        if "deploy" in source_type and result and result not in {"succeeded", "warning"}:
            return True
    return False


def _has_validation_warnings(items: list[Any]) -> bool:
    for item in items:
        payload = _as_dict(item)
        result = (_as_str(payload.get("result")) or "").lower()
        source_type = (_as_str(payload.get("source_type")) or "").lower()
        if "warning" in source_type or result in {"warning", "warnings", "skipped"}:
            return True
    return False


def _has_high_risk_signal(signals: list[str]) -> bool:
    combined = " | ".join(signals).lower()
    return any(term in combined for term in _HIGH_RISK_SIGNAL_TERMS)


def _bool_dict(payload: dict[str, Any]) -> dict[str, bool]:
    return {str(key): bool(value) for key, value in payload.items()}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output
