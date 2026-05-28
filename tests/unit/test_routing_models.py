"""Tests for Phase 7B routing models."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.routing import (
    EvidenceQualityAssessment,
    PromptStrategySelection,
    RiskTierAssessment,
    RoutingDecision,
    RoutingDecisionBundle,
)


def test_routing_decision_serializes() -> None:
    decision = RoutingDecision(
        step="risk_tier",
        decision="high",
        reason="Database change evidence was detected.",
        severity="warning",
        metadata={"flag": "database_change_detected"},
    )

    payload = decision.model_dump(mode="json")

    assert payload["decision"] == "high"
    assert payload["metadata"]["flag"] == "database_change_detected"


def test_routing_decision_bundle_serializes() -> None:
    bundle = RoutingDecisionBundle(
        build_id=5,
        generated_at=datetime(2026, 5, 28, tzinfo=UTC),
        evidence_quality=EvidenceQualityAssessment(
            bucket_1_quality="strong",
            bucket_2_quality="medium",
            bucket_3_quality="weak",
            bucket_1_reasons=[],
            bucket_2_reasons=[],
            bucket_3_reasons=[],
        ),
        prompt_strategy=PromptStrategySelection(
            bucket_1_strategy="bucket_1_standard",
            bucket_2_strategy="bucket_2_missing_tests",
            bucket_3_strategy="bucket_3_conservative_rollback",
            reasons=[],
        ),
        risk_tier=RiskTierAssessment(
            risk_tier="medium",
            reasons=["Test evidence is missing or incomplete."],
            risk_flags={},
            missing_context=["test_results_missing"],
        ),
        decisions=[],
    )

    payload = bundle.model_dump(mode="json")

    assert payload["schema_version"] == "1.0"
    assert payload["risk_tier"]["risk_tier"] == "medium"
