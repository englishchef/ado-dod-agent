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
