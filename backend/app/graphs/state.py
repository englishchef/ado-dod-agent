"""LangGraph state definitions for Phase 7B DoD orchestration."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

DodRunStatus = Literal[
    "started",
    "failed",
    "completed",
    "completed_with_warnings",
    "needs_review",
]

STATUS_STARTED: DodRunStatus = "started"
STATUS_FAILED: DodRunStatus = "failed"
STATUS_COMPLETED: DodRunStatus = "completed"
STATUS_COMPLETED_WITH_WARNINGS: DodRunStatus = "completed_with_warnings"
STATUS_NEEDS_REVIEW: DodRunStatus = "needs_review"


class DodGraphState(TypedDict, total=False):
    """JSON-serializable graph state shared across orchestration nodes."""

    run_id: str
    build_id: int
    organization: str
    project: str
    mode: str
    confidence_threshold: float
    high_risk_confidence_threshold: float
    input: dict[str, Any]
    status: DodRunStatus
    started_at: str | None
    completed_at: str | None
    raw_result: dict[str, Any] | None
    canonical_result: dict[str, Any] | None
    evidence_result: dict[str, Any] | None
    evidence_quality: dict[str, Any] | None
    prompt_strategy: dict[str, Any] | None
    risk_tier: dict[str, Any] | None
    routing_decisions: list[dict[str, Any]]
    llm_outputs: dict[str, Any] | None
    validated_output: dict[str, Any] | None
    service_now_payload: dict[str, Any] | None
    confidence: dict[str, Any] | None
    rule_evaluation: dict[str, Any] | None
    artifact_paths: dict[str, str]
    phase_durations_ms: dict[str, int]
    warnings: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    run_summary: dict[str, Any]
    routing_decisions_bundle: dict[str, Any]
