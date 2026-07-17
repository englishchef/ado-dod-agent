"""Prompt strategy selection for Phase 7B routing."""

from __future__ import annotations

from typing import Any

from backend.app.models.routing import (
    EvidenceQualityAssessment,
    PromptStrategySelection,
    RiskTierAssessment,
)
from backend.app.services.evidence.bucket_3_selection import deployment_action_kind


def select_prompt_strategy(
    evidence_quality: EvidenceQualityAssessment,
    risk_tier: RiskTierAssessment,
    evidence_bundle: dict[str, Any],
) -> PromptStrategySelection:
    """Select deterministic prompt strategies for each LLM bucket."""

    reasons: list[str] = []

    if evidence_quality.bucket_1_quality == "weak":
        bucket_1_strategy = "bucket_1_low_evidence"
        reasons.append("Bucket 1 evidence is weak, so low-evidence wording is required.")
    else:
        bucket_1_strategy = "bucket_1_standard"
        reasons.append("Bucket 1 evidence supports the standard change-intent prompt.")

    bucket_2 = _as_dict(evidence_bundle.get("bucket_2"))
    test_evidence = _as_dict(bucket_2.get("test_evidence"))
    total_tests = _as_int(test_evidence.get("total_tests")) or 0
    missing_test_context = _as_list(test_evidence.get("missing_test_context"))
    if total_tests > 0:
        bucket_2_strategy = "bucket_2_standard"
        reasons.append("Collected test evidence is available for Bucket 2.")
    else:
        bucket_2_strategy = "bucket_2_missing_tests"
        if missing_test_context:
            reasons.append("Bucket 2 has explicit missing test context.")
        else:
            reasons.append("Bucket 2 has no collected test results.")

    bucket_3 = _as_dict(evidence_bundle.get("bucket_3"))
    backout_step_derivation = _as_dict(bucket_3.get("backout_step_derivation"))
    normalized_actions = _as_list(backout_step_derivation.get("normalized_actions"))
    if not normalized_actions:
        uat_deployment = _as_dict(bucket_3.get("uat_deployment"))
        normalized_actions = [
            kind
            for item in _as_list(uat_deployment.get("activities"))
            if isinstance(item, dict)
            and (kind := deployment_action_kind(str(item.get("name") or ""))) is not None
        ]
    if risk_tier.risk_tier == "high":
        bucket_3_strategy = "bucket_3_high_risk"
        reasons.append("Risk tier is high, so high-risk rollback/risk wording is required.")
    elif not normalized_actions or backout_step_derivation.get("fallback_used") is True:
        bucket_3_strategy = "bucket_3_conservative_rollback"
        reasons.append(
            "No normalized deployment action supports a specific reversal step, so "
            "conservative rollback wording is required."
        )
    else:
        bucket_3_strategy = "bucket_3_standard"
        reasons.append("Normalized deployment actions support the standard Bucket 3 prompt.")

    return PromptStrategySelection(
        bucket_1_strategy=bucket_1_strategy,
        bucket_2_strategy=bucket_2_strategy,
        bucket_3_strategy=bucket_3_strategy,
        reasons=reasons,
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None
