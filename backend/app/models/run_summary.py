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


class DodRunSummary(BaseModel):
    """Persisted summary for one end-to-end DoD agent run."""

    schema_version: str = "1.0"
    run_id: str
    build_id: int
    organization: str
    project: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    service_now_payload: dict[str, Any] | None = None
    confidence: dict[str, Any] | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    warnings: list[RunIssue] = Field(default_factory=list)
    errors: list[RunIssue] = Field(default_factory=list)
