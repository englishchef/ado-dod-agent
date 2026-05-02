"""Output schemas returned by API endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from backend.app.models.raw import (
    CollectorError,
    CollectorStatus,
    RawArtifactPaths,
    RawCollectionResult,
    RawCollectionSummary,
)


class HealthResponse(BaseModel):
    """Service liveness payload."""

    status: str = Field(description="High-level health status.")
    service: str = Field(description="Service name.")
    environment: str = Field(description="Runtime environment.")


class RunGenerationResponse(BaseModel):
    """Placeholder run generation response for Phase 0."""

    status: str = Field(description="Request status.")
    message: str = Field(description="Human-readable summary.")


class SmokeAuthResponse(BaseModel):
    """Response model for auth smoke validation endpoints."""

    status: str = Field(description="Smoke call status.")
    message: str = Field(description="Human-readable smoke summary.")
    authentication_succeeded: bool = Field(
        description="Whether bearer token acquisition succeeded."
    )
    organization: str = Field(description="Target Azure DevOps organization.")
    project: str = Field(description="Target Azure DevOps project.")


class NormalizeRawResponse(BaseModel):
    """Response model for canonical normalization endpoint."""

    status: str = Field(description="Normalization status.")
    message: str = Field(description="Human-readable summary.")
    build_id: int = Field(description="Build id for normalized output.")
    pipeline_name: str | None = Field(default=None)
    source_branch: str | None = Field(default=None)
    source_version: str | None = Field(default=None)
    work_item_count: int = Field(default=0)
    commit_count: int = Field(default=0)
    pull_request_count: int = Field(default=0)
    stage_count: int = Field(default=0)
    job_count: int = Field(default=0)
    task_count: int = Field(default=0)
    artifact_count: int = Field(default=0)
    test_run_count: int = Field(default=0)
    failed_test_count: int = Field(default=0)
    risk_flags: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    canonical_path: str = Field(description="Path to canonical JSON artifact.")
    details: dict[str, Any] | None = Field(
        default=None,
        description="Optional extension map for future phases.",
    )


class BuildEvidenceResponse(BaseModel):
    """Response model for deterministic evidence bucket generation endpoint."""

    status: str = Field(description="Evidence generation status.")
    message: str = Field(description="Human-readable summary.")
    build_id: int = Field(description="Build id for evidence output.")
    pipeline_name: str | None = Field(default=None)
    bucket_1_counts: dict[str, int] = Field(default_factory=dict)
    bucket_2_counts: dict[str, int] = Field(default_factory=dict)
    bucket_3_counts: dict[str, int] = Field(default_factory=dict)
    evidence_gap_counts: dict[str, int] = Field(default_factory=dict)
    truncation_applied: bool = Field(default=False)
    output_paths: dict[str, str] = Field(default_factory=dict)


__all__ = [
    "HealthResponse",
    "RunGenerationResponse",
    "SmokeAuthResponse",
    "NormalizeRawResponse",
    "BuildEvidenceResponse",
    "RawCollectionResult",
    "RawCollectionSummary",
    "RawArtifactPaths",
    "CollectorStatus",
    "CollectorError",
]

