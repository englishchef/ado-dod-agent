"""API request/response models for Phase 8 pipeline-facing endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GenerateRunRequest(BaseModel):
    """Request body for running the DoD agent workflow."""

    organization: str = Field(min_length=1)
    project: str = Field(min_length=1)
    build_id: int = Field(gt=0)
    mode: Literal["local", "pipeline", "dev", "test"] = "pipeline"
    correlation_id: str | None = None


class ApiIssue(BaseModel):
    """API-safe issue model."""

    severity: str
    code: str
    message: str
    phase: str | None = None


class GenerateRunResponse(BaseModel):
    """Response body for completed DoD agent workflow runs."""

    run_id: str
    correlation_id: str | None = None
    status: str
    build_id: int
    organization: str
    project: str
    service_now_payload: dict[str, Any] | None = None
    confidence: dict[str, Any] | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    warnings: list[ApiIssue] = Field(default_factory=list)
    errors: list[ApiIssue] = Field(default_factory=list)


class ArtifactResponse(BaseModel):
    """Read-only JSON artifact response."""

    build_id: int
    artifact_type: str
    path: str
    content: dict[str, Any]


class ReadyResponse(BaseModel):
    """Application readiness response."""

    status: str
    missing_config: list[str] = Field(default_factory=list)
    configured: list[str] = Field(default_factory=list)
