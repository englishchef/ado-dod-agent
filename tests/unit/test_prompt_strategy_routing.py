"""Tests for Phase 7B prompt strategy routing."""

from __future__ import annotations

from backend.app.models.routing import EvidenceQualityAssessment, RiskTierAssessment
from backend.app.services.routing.prompt_strategy import select_prompt_strategy


def _quality(bucket_1: str = "strong") -> EvidenceQualityAssessment:
    return EvidenceQualityAssessment(
        bucket_1_quality=bucket_1,  # type: ignore[arg-type]
        bucket_2_quality="medium",
        bucket_3_quality="medium",
        bucket_1_reasons=[],
        bucket_2_reasons=[],
        bucket_3_reasons=[],
    )


def _risk(risk_tier: str = "medium") -> RiskTierAssessment:
    return RiskTierAssessment(
        risk_tier=risk_tier,  # type: ignore[arg-type]
        reasons=[],
        risk_flags={},
        missing_context=[],
    )


def test_bucket_2_missing_tests_selects_missing_tests_strategy() -> None:
    result = select_prompt_strategy(
        _quality(),
        _risk(),
        {"bucket_2": {"test_evidence": {"total_tests": 0}}},
    )

    assert result.bucket_2_strategy == "bucket_2_missing_tests"


def test_weak_bucket_1_selects_low_evidence_strategy() -> None:
    result = select_prompt_strategy(_quality("weak"), _risk(), {})

    assert result.bucket_1_strategy == "bucket_1_low_evidence"


def test_high_risk_selects_high_risk_bucket_3_strategy() -> None:
    result = select_prompt_strategy(_quality(), _risk("high"), {"bucket_3": {}})

    assert result.bucket_3_strategy == "bucket_3_high_risk"


def test_missing_uat_activity_selects_conservative_rollback() -> None:
    result = select_prompt_strategy(
        _quality(),
        _risk("medium"),
        {"bucket_3": {"uat_deployment": {"activities": []}}},
    )

    assert result.bucket_3_strategy == "bucket_3_conservative_rollback"


def test_uat_activity_evidence_selects_standard_bucket_3_strategy() -> None:
    result = select_prompt_strategy(
        _quality(),
        _risk("medium"),
        {
            "bucket_3": {
                "backout_step_derivation": {
                    "normalized_actions": ["solution_deployment"],
                    "fallback_used": False,
                },
                "uat_deployment": {
                    "activities": [{"name": "Deploy solution package"}],
                }
            }
        },
    )

    assert result.bucket_3_strategy == "bucket_3_standard"


def test_selected_stage_without_normalized_actions_uses_conservative_wording() -> None:
    result = select_prompt_strategy(
        _quality(),
        _risk("medium"),
        {
            "bucket_3": {
                "backout_time_derivation": {"selected_environment": "UAT"},
                "backout_step_derivation": {
                    "normalized_actions": [],
                    "fallback_used": True,
                },
            }
        },
    )

    assert result.bucket_3_strategy == "bucket_3_conservative_rollback"
