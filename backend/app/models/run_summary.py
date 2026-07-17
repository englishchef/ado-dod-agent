"""Phase 7A orchestration run summary models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunIssue(BaseModel):
    """Structured non-sensitive issue captured during orchestration."""

    severity: str
    code: str
    message: str
    phase: str | None = None
    diagnostics: dict[str, Any] | None = None


class DodRunSummary(BaseModel):
    """Persisted summary for one end-to-end DoD agent run."""

    schema_version: str = "1.0"
    run_id: str
    build_id: int
    organization: str
    project: str
    correlation_id: str | None = None
    pipeline_id: str | None = None
    pipeline_name: str | None = None
    build_number: str | None = None
    branch: str | None = None
    requested_by: str | None = None
    source: str | None = None
    mode: str | None = None
    status: str
    rule_recommended_status: str | None = None
    highest_rule_severity: str | None = None
    final_confidence: float | None = None
    test_completeness_score: dict[str, Any] | None = None
    storage_backend: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    phase_durations_ms: dict[str, int] = Field(default_factory=dict)
    artifact_count: int | None = None
    service_now_payload: dict[str, Any] | None = None
    confidence: dict[str, Any] | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    warnings: list[RunIssue] = Field(default_factory=list)
    errors: list[RunIssue] = Field(default_factory=list)
