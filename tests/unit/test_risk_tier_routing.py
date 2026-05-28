"""Tests for Phase 7B risk tier routing."""

from __future__ import annotations

from backend.app.services.routing.risk_tier import assess_risk_tier


def test_database_change_is_high_risk() -> None:
    result = assess_risk_tier(
        {"bucket_3": {"risk_flags": {"database_change_detected": True}}}
    )

    assert result.risk_tier == "high"


def test_infrastructure_change_is_high_risk() -> None:
    result = assess_risk_tier(
        {"bucket_3": {"risk_flags": {"infrastructure_change_detected": True}}}
    )

    assert result.risk_tier == "high"


def test_dependency_config_feature_flags_are_medium_risk() -> None:
    for flag in (
        "dependency_change_detected",
        "config_change_detected",
        "feature_flag_change_detected",
    ):
        result = assess_risk_tier({"bucket_3": {"risk_flags": {flag: True}}})
        assert result.risk_tier == "medium"


def test_missing_test_context_is_medium_risk() -> None:
    result = assess_risk_tier(
        {"bucket_2": {"test_evidence": {"total_tests": 0, "missing_test_context": ["missing"]}}}
    )

    assert result.risk_tier == "medium"


def test_no_major_flags_with_sufficient_artifacts_is_low_risk() -> None:
    result = assess_risk_tier(
        {
            "bucket_2": {"test_evidence": {"total_tests": 3}},
            "bucket_3": {
                "service_context": {"source_version": "abc"},
                "artifact_evidence": [{"name": "drop"}],
                "failed_or_warning_evidence": [],
                "risk_flags": {
                    "database_change_detected": False,
                    "infrastructure_change_detected": False,
                    "dependency_change_detected": False,
                    "config_change_detected": False,
                    "feature_flag_change_detected": False,
                },
            },
        }
    )

    assert result.risk_tier == "low"
    assert "no risk" not in " ".join(result.reasons).lower()
