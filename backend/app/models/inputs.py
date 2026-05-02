"""Input schemas for API operations."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateRunInput(BaseModel):
    """Phase-0 placeholder payload for generate-run orchestration."""

    organization: str = Field(min_length=1, description="Azure DevOps organization name.")
    project: str = Field(min_length=1, description="Azure DevOps project name.")
    build_id: int = Field(description="Azure DevOps build identifier.")
    pipeline_name: str | None = Field(
        default=None,
        description="Optional pipeline display name.",
    )
    repository: str | None = Field(
        default=None,
        description="Optional repository name.",
    )
    mode: str = Field(
        default="local",
        description="Execution mode placeholder for future runtime routing.",
    )


class CollectRawInput(GenerateRunInput):
    """Phase-2 request model for raw metadata collection."""

    include_tests: bool = Field(
        default=True,
        description="Whether test runs and results should be collected.",
    )
    include_pull_requests: bool = Field(
        default=True,
        description="Whether pull-request metadata lookup should be attempted.",
    )
    include_artifacts: bool = Field(
        default=True,
        description="Whether build artifact metadata should be collected.",
    )
    max_test_results_per_run: int = Field(
        default=200,
        ge=1,
        le=5000,
        description="Max number of test results to fetch per run.",
    )


class NormalizeRawInput(BaseModel):
    """Phase-3 request model for deterministic canonical normalization."""

    build_id: int = Field(description="Azure DevOps build identifier.")
    raw_bundle_path: str | None = Field(
        default=None,
        description="Optional absolute/relative path to a raw bundle JSON file.",
    )
    organization: str | None = Field(
        default=None,
        description="Optional organization override for metadata.",
    )
    project: str | None = Field(
        default=None,
        description="Optional project override for metadata.",
    )
    mode: str = Field(default="local", description="Execution mode placeholder.")


class BuildEvidenceInput(BaseModel):
    """Phase-4 request model for deterministic evidence bucket generation."""

    build_id: int = Field(description="Azure DevOps build identifier.")
    canonical_path: str | None = Field(
        default=None,
        description="Optional absolute/relative path to a canonical JSON file.",
    )
    max_items_per_section: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum evidence entries retained per section.",
    )
    mode: str = Field(default="local", description="Execution mode placeholder.")
