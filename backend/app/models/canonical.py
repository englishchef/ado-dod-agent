"""Canonical normalized models for Phase 3."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CanonicalBaseModel(BaseModel):
    """Base model config for canonical payloads."""

    model_config = ConfigDict(extra="ignore")


class RunContext(CanonicalBaseModel):
    build_id: int
    build_number: str | None = None
    pipeline_id: int | None = None
    pipeline_name: str | None = None
    repository_id: str | None = None
    repository_name: str | None = None
    repository_type: str | None = None
    source_branch: str | None = None
    source_version: str | None = None
    requested_by: str | None = None
    requested_for: str | None = None
    queue_time: datetime | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    status: str | None = None
    result: str | None = None
    reason: str | None = None
    url: str | None = None
    web_url: str | None = None


class CanonicalWorkItem(CanonicalBaseModel):
    id: int
    type: str | None = None
    title: str | None = None
    state: str | None = None
    reason: str | None = None
    assigned_to: str | None = None
    created_by: str | None = None
    changed_by: str | None = None
    area_path: str | None = None
    iteration_path: str | None = None
    tags: list[str] = Field(default_factory=list)
    description: str | None = None
    acceptance_criteria: str | None = None
    priority: int | None = None
    business_value: int | None = None
    url: str | None = None
    source_ref: str | None = None


class CanonicalCommit(CanonicalBaseModel):
    id: str
    message: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    authored_at: datetime | None = None
    committer_name: str | None = None
    committed_at: datetime | None = None
    url: str | None = None
    source_ref: str | None = None


class CanonicalPullRequest(CanonicalBaseModel):
    id: int
    title: str | None = None
    description: str | None = None
    status: str | None = None
    created_by: str | None = None
    source_branch: str | None = None
    target_branch: str | None = None
    merge_status: str | None = None
    is_draft: bool | None = None
    reviewers: list[str] = Field(default_factory=list)
    commit_ids: list[str] = Field(default_factory=list)
    url: str | None = None
    source_ref: str | None = None


class ChangeContext(CanonicalBaseModel):
    work_items: list[CanonicalWorkItem] = Field(default_factory=list)
    commits: list[CanonicalCommit] = Field(default_factory=list)
    pull_requests: list[CanonicalPullRequest] = Field(default_factory=list)
    change_summary_signals: list[str] = Field(default_factory=list)
    missing_change_context: list[str] = Field(default_factory=list)


class CanonicalStage(CanonicalBaseModel):
    id: str | None = None
    name: str
    state: str | None = None
    result: str | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    duration_seconds: float | None = None
    source_ref: str | None = None


class CanonicalJob(CanonicalBaseModel):
    id: str | None = None
    name: str
    parent_id: str | None = None
    state: str | None = None
    result: str | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    duration_seconds: float | None = None
    source_ref: str | None = None


class CanonicalTask(CanonicalBaseModel):
    id: str | None = None
    name: str
    parent_id: str | None = None
    type: str | None = None
    state: str | None = None
    result: str | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    duration_seconds: float | None = None
    log_url: str | None = None
    source_ref: str | None = None


class CanonicalArtifact(CanonicalBaseModel):
    name: str
    type: str | None = None
    resource_type: str | None = None
    download_url: str | None = None
    source_ref: str | None = None


class ExecutionContext(CanonicalBaseModel):
    stages: list[CanonicalStage] = Field(default_factory=list)
    jobs: list[CanonicalJob] = Field(default_factory=list)
    tasks: list[CanonicalTask] = Field(default_factory=list)
    artifacts: list[CanonicalArtifact] = Field(default_factory=list)
    deployment_signals: list[str] = Field(default_factory=list)
    implementation_signals: list[str] = Field(default_factory=list)
    validation_signals: list[str] = Field(default_factory=list)
    missing_execution_context: list[str] = Field(default_factory=list)


class CanonicalTestRun(CanonicalBaseModel):
    id: int
    name: str | None = None
    state: str | None = None
    outcome: str | None = None
    total_tests: int | None = None
    passed_tests: int | None = None
    failed_tests: int | None = None
    skipped_tests: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    url: str | None = None
    source_ref: str | None = None


class CanonicalTestSummary(CanonicalBaseModel):
    total_runs: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    pass_rate: float | None = None


class CanonicalTestResult(CanonicalBaseModel):
    id: int | str | None = None
    test_run_id: int | None = None
    test_name: str | None = None
    outcome: str | None = None
    duration_ms: float | None = None
    error_message: str | None = None
    stack_trace: str | None = None
    source_ref: str | None = None


class CanonicalScanSummary(CanonicalBaseModel):
    security_status: str | None = None
    code_quality_status: str | None = None
    dependency_status: str | None = None
    scan_signals: list[str] = Field(default_factory=list)
    missing_scan_context: list[str] = Field(default_factory=list)


class QualityContext(CanonicalBaseModel):
    test_runs: list[CanonicalTestRun] = Field(default_factory=list)
    test_summary: CanonicalTestSummary = Field(default_factory=CanonicalTestSummary)
    failed_tests: list[CanonicalTestResult] = Field(default_factory=list)
    warning_tests: list[CanonicalTestResult] = Field(default_factory=list)
    scan_summary: CanonicalScanSummary | None = None
    quality_signals: list[str] = Field(default_factory=list)
    missing_quality_context: list[str] = Field(default_factory=list)


class RiskContext(CanonicalBaseModel):
    impacted_components: list[str] = Field(default_factory=list)
    config_change_detected: bool = False
    database_change_detected: bool = False
    infrastructure_change_detected: bool = False
    dependency_change_detected: bool = False
    feature_flag_change_detected: bool = False
    rollback_indicators: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    missing_risk_context: list[str] = Field(default_factory=list)


class NormalizationMetadata(CanonicalBaseModel):
    raw_collection_status: str | None = None
    raw_collector_errors: list[str] = Field(default_factory=list)
    normalized_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CanonicalDodDocument(CanonicalBaseModel):
    schema_version: str = "1.0"
    build_id: int
    organization: str
    project: str
    generated_at: datetime
    source_raw_bundle_path: str | None = None
    run_context: RunContext
    change_context: ChangeContext
    execution_context: ExecutionContext
    quality_context: QualityContext
    risk_context: RiskContext
    normalization_metadata: NormalizationMetadata
