"""Raw metadata collection models for Phase 2."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CollectionStatus = Literal["completed", "partial", "failed"]
CollectorState = Literal["completed", "partial", "failed", "skipped"]
CollectorSeverity = Literal["low", "medium", "high"]


class CollectorError(BaseModel):
    """Safe, structured collector error detail."""

    collector: str = Field(description="Collector name that raised/recorded the error.")
    message: str = Field(description="Safe error summary without sensitive data.")
    severity: CollectorSeverity = Field(default="medium")
    status_code: int | None = Field(default=None, description="HTTP status code when relevant.")
    path: str | None = Field(default=None, description="ADO API path when relevant.")


class CollectorStatus(BaseModel):
    """Collector execution status and counters."""

    name: str = Field(description="Collector name.")
    status: CollectorState = Field(description="Collector completion state.")
    records_collected: int = Field(
        default=0,
        ge=0,
        description="Count of top-level collected records/items.",
    )
    skipped_reason: str | None = Field(default=None)


class RawArtifactPaths(BaseModel):
    """Local artifact file paths for collected raw metadata."""

    build: str | None = None
    timeline: str | None = None
    work_item_refs: str | None = None
    work_items: str | None = None
    changes: str | None = None
    artifacts: str | None = None
    pull_requests: str | None = None
    test_runs: str | None = None
    test_results: str | None = None
    raw_bundle: str | None = None


class RawCollectionSummary(BaseModel):
    """High-level item counts from raw collection."""

    timeline_record_count: int = 0
    artifact_count: int = 0
    work_item_ref_count: int = 0
    work_item_count: int = 0
    change_count: int = 0
    pull_request_count: int = 0
    test_run_count: int = 0
    test_result_count: int = 0


class RawCollectionResult(BaseModel):
    """Top-level response for a raw metadata collection run."""

    collection_run_id: str
    build_id: int
    status: CollectionStatus
    collected_at: datetime
    pipeline_name: str | None = None
    branch: str | None = None
    build_status: str | None = None
    build_result: str | None = None
    summary: RawCollectionSummary
    artifact_paths: RawArtifactPaths
    collector_statuses: list[CollectorStatus]
    errors: list[CollectorError] = Field(default_factory=list)
