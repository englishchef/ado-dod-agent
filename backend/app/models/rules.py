"""Deterministic rule evaluation models for Phase 9."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RuleSeverity = Literal["info", "warning", "review", "error"]
RuleCategory = Literal[
    "test_completeness",
    "unsupported_claim",
    "backout_plan",
    "risk_impact",
    "field_quality",
    "traceability",
    "confidence",
    "general",
]
RecommendedStatus = Literal["completed", "completed_with_warnings", "needs_review", "failed"]


class RuleBaseModel(BaseModel):
    """Base config for rule evaluation payloads."""

    model_config = ConfigDict(extra="forbid")


class RuleResult(RuleBaseModel):
    rule_id: str
    category: RuleCategory
    severity: RuleSeverity
    message: str
    field_name: str | None = None
    bucket: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    rationale: str | None = None
    recommendation: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TestCompletenessScore(RuleBaseModel):
    overall_score: float = Field(ge=0, le=1)
    functional_score: float = Field(ge=0, le=1)
    nonfunctional_score: float = Field(ge=0, le=1)
    coverage_score: float = Field(ge=0, le=1)
    security_score: float = Field(ge=0, le=1)
    deployment_validation_score: float = Field(ge=0, le=1)
    traceability_score: float = Field(ge=0, le=1)
    rationale: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)


class ConfidenceAdjustment(RuleBaseModel):
    target: Literal["overall", "bucket_1", "bucket_2", "bucket_3"]
    adjustment: float
    reason: str
    rule_id: str | None = None


class RuleEvaluationSummary(RuleBaseModel):
    highest_severity: RuleSeverity
    recommended_status: RecommendedStatus
    info_count: int = 0
    warning_count: int = 0
    review_count: int = 0
    error_count: int = 0
    triggered_rule_count: int = 0


class RuleEvaluation(RuleBaseModel):
    schema_version: str = "1.0"
    build_id: int
    generated_at: datetime
    test_completeness_score: TestCompletenessScore
    rules_triggered: list[RuleResult] = Field(default_factory=list)
    confidence_adjustments: list[ConfidenceAdjustment] = Field(default_factory=list)
    summary: RuleEvaluationSummary
    source_paths: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
