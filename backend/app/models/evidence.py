"""Evidence bucket models for Phase 4."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceBaseModel(BaseModel):
    """Base model config for evidence payloads."""

    model_config = ConfigDict(extra="ignore")


class EvidenceServiceContext(EvidenceBaseModel):
    build_id: int
    build_number: str | None = None
    pipeline_name: str | None = None
    repository_name: str | None = None
    source_branch: str | None = None
    source_version: str | None = None
    result: str | None = None
    status: str | None = None
    requested_by: str | None = None


class WorkItemEvidence(EvidenceBaseModel):
    id: int
    type: str | None = None
    title: str | None = None
    state: str | None = None
    description: str | None = None
    acceptance_criteria: str | None = None
    priority: int | None = None
    business_value: int | None = None
    tags: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class CommitEvidence(EvidenceBaseModel):
    id: str
    message: str | None = None
    author_name: str | None = None
    authored_at: datetime | None = None
    source_ref: str | None = None


class PullRequestEvidence(EvidenceBaseModel):
    id: int
    title: str | None = None
    description: str | None = None
    status: str | None = None
    source_branch: str | None = None
    target_branch: str | None = None
    reviewers: list[str] = Field(default_factory=list)
    commit_ids: list[str] = Field(default_factory=list)
    source_ref: str | None = None


class StageEvidence(EvidenceBaseModel):
    name: str
    result: str | None = None
    state: str | None = None
    duration_seconds: float | None = None
    source_ref: str | None = None


class JobEvidence(EvidenceBaseModel):
    name: str
    result: str | None = None
    state: str | None = None
    duration_seconds: float | None = None
    source_ref: str | None = None


class TaskEvidence(EvidenceBaseModel):
    name: str
    type: str | None = None
    result: str | None = None
    state: str | None = None
    duration_seconds: float | None = None
    log_url: str | None = None
    source_ref: str | None = None


class ArtifactEvidence(EvidenceBaseModel):
    name: str
    type: str | None = None
    resource_type: str | None = None
    download_url: str | None = None
    source_ref: str | None = None


class TestEvidenceSummary(EvidenceBaseModel):
    total_runs: int = 0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    pass_rate: float | None = None
    failed_tests_sample: list[str] = Field(default_factory=list)
    warning_tests_sample: list[str] = Field(default_factory=list)
    missing_test_context: list[str] = Field(default_factory=list)


class RiskFlagsEvidence(EvidenceBaseModel):
    config_change_detected: bool = False
    database_change_detected: bool = False
    infrastructure_change_detected: bool = False
    dependency_change_detected: bool = False
    feature_flag_change_detected: bool = False


class UatDeploymentActivityEvidence(EvidenceBaseModel):
    name: str
    status: str | None = None
    duration_seconds: float | None = None
    source_ref: str | None = None


class UatDeploymentEvidence(EvidenceBaseModel):
    stage_name: str | None = None
    selected_environment: str | None = None
    stage_start_time: datetime | None = None
    stage_finish_time: datetime | None = None
    activities: list[UatDeploymentActivityEvidence] = Field(default_factory=list)
    total_deployment_duration_seconds: float | None = None


class LowerEnvironmentStageCandidateEvidence(EvidenceBaseModel):
    stage_name: str
    normalized_environment: str | None = None
    state: str | None = None
    result: str | None = None
    start_time: datetime | None = None
    finish_time: datetime | None = None
    duration_seconds: float | None = None
    deployment_activities: list[str] = Field(default_factory=list)
    source_ref: str | None = None
    selected: bool = False


class RejectedStageEvidence(EvidenceBaseModel):
    stage_name: str
    reason: str


class BackoutTimeDerivationEvidence(EvidenceBaseModel):
    calculation_method: str = "lower_environment_stage_duration"
    environment_priority: list[str] = Field(default_factory=list)
    selected_environment: str | None = None
    selected_stage_name: str | None = None
    stage_start_time: datetime | None = None
    stage_finish_time: datetime | None = None
    source_duration_seconds: float | None = None
    rounding_rule: str = "round_up_to_nearest_5_minutes"
    final_estimate_minutes: int | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class ApplicationCandidateScoreEvidence(EvidenceBaseModel):
    candidate: str
    score: int
    sources: list[str] = Field(default_factory=list)


class ApplicationResolutionEvidence(EvidenceBaseModel):
    selected_application: str
    display_name: str
    selection_reason: str
    candidate_scores: list[ApplicationCandidateScoreEvidence] = Field(default_factory=list)


class ResiliencyEvidence(EvidenceBaseModel):
    active_active: bool = False
    alternate_region: str | None = None
    rolling_deployment: bool = False
    traffic_shift: bool = False
    passive_instance_available: bool = False
    evidence_refs: list[str] = Field(default_factory=list)


class FailureWarningEvidence(EvidenceBaseModel):
    source_type: str
    name: str | None = None
    result: str | None = None
    message: str | None = None
    source_ref: str | None = None


class ChangeIntentEvidence(EvidenceBaseModel):
    target_fields: list[str] = Field(default_factory=list)
    service_context: EvidenceServiceContext
    work_item_evidence: list[WorkItemEvidence] = Field(default_factory=list)
    commit_evidence: list[CommitEvidence] = Field(default_factory=list)
    pull_request_evidence: list[PullRequestEvidence] = Field(default_factory=list)
    change_summary_signals: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)


class ExecutionValidationEvidence(EvidenceBaseModel):
    target_fields: list[str] = Field(default_factory=list)
    service_context: EvidenceServiceContext
    stage_evidence: list[StageEvidence] = Field(default_factory=list)
    job_evidence: list[JobEvidence] = Field(default_factory=list)
    task_evidence: list[TaskEvidence] = Field(default_factory=list)
    artifact_evidence: list[ArtifactEvidence] = Field(default_factory=list)
    test_evidence: TestEvidenceSummary
    implementation_signals: list[str] = Field(default_factory=list)
    validation_signals: list[str] = Field(default_factory=list)
    deployment_signals: list[str] = Field(default_factory=list)
    quality_signals: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)


class RollbackRiskEvidence(EvidenceBaseModel):
    target_fields: list[str] = Field(default_factory=list)
    service_context: EvidenceServiceContext
    artifact_evidence: list[ArtifactEvidence] = Field(default_factory=list)
    rollback_indicators: list[str] = Field(default_factory=list)
    impacted_components: list[str] = Field(default_factory=list)
    risk_flags: RiskFlagsEvidence
    risk_signals: list[str] = Field(default_factory=list)
    uat_deployment: UatDeploymentEvidence = Field(default_factory=UatDeploymentEvidence)
    environment_candidates: list[LowerEnvironmentStageCandidateEvidence] = Field(
        default_factory=list
    )
    rejected_stages: list[RejectedStageEvidence] = Field(default_factory=list)
    backout_time_derivation: BackoutTimeDerivationEvidence = Field(
        default_factory=BackoutTimeDerivationEvidence
    )
    resiliency_evidence: ResiliencyEvidence = Field(default_factory=ResiliencyEvidence)
    application_candidates: list[str] = Field(default_factory=list)
    application_resolution: ApplicationResolutionEvidence | None = None
    planned_impact_evidence: list[str] = Field(default_factory=list)
    high_risk_evidence: list[str] = Field(default_factory=list)
    failed_or_warning_evidence: list[FailureWarningEvidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)


class EvidenceGenerationMetadata(EvidenceBaseModel):
    canonical_schema_version: str | None = None
    generated_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    truncation_applied: bool = False
    max_items_per_section: int = 10


class EvidenceSourceRef(EvidenceBaseModel):
    friendly_ref: str
    original_ref: str | None = None
    source_type: str
    display_name: str | None = None


class EvidenceBundle(EvidenceBaseModel):
    schema_version: str = "1.0"
    build_id: int
    organization: str
    project: str
    generated_at: datetime
    source_canonical_path: str | None = None
    bucket_1: ChangeIntentEvidence
    bucket_2: ExecutionValidationEvidence
    bucket_3: RollbackRiskEvidence
    generation_metadata: EvidenceGenerationMetadata
    source_ref_map: dict[str, EvidenceSourceRef] = Field(default_factory=dict)
