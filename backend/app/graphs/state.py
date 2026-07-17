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
    correlation_id: str | None
    requested_by: str | None
    source: str | None
    metadata: dict[str, Any]
    confidence_threshold: float
    high_risk_confidence_threshold: float
    input: dict[str, Any]
    status: DodRunStatus
    current_phase: str | None
    started_at: str | None
    completed_at: str | None
    raw_summary: dict[str, Any] | None
    canonical_summary: dict[str, Any] | None
    evidence_summary: dict[str, Any] | None
    bucket_3_summary: dict[str, Any] | None
    validation_summary: dict[str, Any] | None
    rule_evaluation_summary: dict[str, Any] | None

    # Deprecated compatibility keys. Production nodes clear or omit these large
    # values and load the corresponding document from ArtifactStore by reference.
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


GRAPH_STATE_KEYS = frozenset(DodGraphState.__annotations__)

# Keys that can retain whole persisted documents in legacy callers. They are
# explicitly cleared when an unsafe state must be compacted before checkpointing.
LEGACY_LARGE_STATE_KEYS = (
    "raw_result",
    "canonical_result",
    "evidence_result",
    "llm_outputs",
    "validated_output",
    "rule_evaluation",
    "run_summary",
    "routing_decisions_bundle",
)
