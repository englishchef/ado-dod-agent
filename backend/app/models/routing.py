"""Deterministic routing models for Phase 7B orchestration."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

IssueSeverity = Literal["info", "warning", "error"]
EvidenceQuality = Literal["strong", "medium", "weak"]
RiskTier = Literal["low", "medium", "high"]


class RoutingDecision(BaseModel):
    """One audited routing decision made by the graph."""

    step: str
    decision: str
    reason: str
    severity: IssueSeverity = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceQualityAssessment(BaseModel):
    """Quality assessment for prompt-ready evidence buckets."""

    bucket_1_quality: EvidenceQuality
    bucket_2_quality: EvidenceQuality
    bucket_3_quality: EvidenceQuality
    bucket_1_reasons: list[str] = Field(default_factory=list)
    bucket_2_reasons: list[str] = Field(default_factory=list)
    bucket_3_reasons: list[str] = Field(default_factory=list)


class PromptStrategySelection(BaseModel):
    """Selected prompt strategies for each bucket."""

    bucket_1_strategy: str
    bucket_2_strategy: str
    bucket_3_strategy: str
    reasons: list[str] = Field(default_factory=list)


class RiskTierAssessment(BaseModel):
    """Risk tier assessment derived from deterministic evidence."""

    risk_tier: RiskTier
    reasons: list[str] = Field(default_factory=list)
    risk_flags: dict[str, bool] = Field(default_factory=dict)
    missing_context: list[str] = Field(default_factory=list)


class RoutingDecisionBundle(BaseModel):
    """Persisted routing audit artifact."""

    schema_version: str = "1.0"
    build_id: int
    generated_at: datetime
    evidence_quality: EvidenceQualityAssessment | None = None
    prompt_strategy: PromptStrategySelection | None = None
    risk_tier: RiskTierAssessment | None = None
    decisions: list[RoutingDecision] = Field(default_factory=list)
