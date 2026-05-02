"""Output schemas returned by API endpoints."""

from __future__ import annotations

from backend.app.models.raw import (
    CollectorError,
    CollectorStatus,
    RawArtifactPaths,
    RawCollectionResult,
    RawCollectionSummary,
)
from pydantic import BaseModel, Field


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


__all__ = [
    "HealthResponse",
    "RunGenerationResponse",
    "SmokeAuthResponse",
    "RawCollectionResult",
    "RawCollectionSummary",
    "RawArtifactPaths",
    "CollectorStatus",
    "CollectorError",
]

