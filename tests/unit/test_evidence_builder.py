"""Tests for deterministic Phase-4 evidence bucket builder."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.canonical import (
    CanonicalArtifact,
    CanonicalCommit,
    CanonicalDodDocument,
    CanonicalJob,
    CanonicalPullRequest,
    CanonicalStage,
    CanonicalTask,
    CanonicalTestResult,
    CanonicalTestRun,
    CanonicalTestSummary,
    CanonicalWorkItem,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)
from backend.app.services.evidence.builder import (
    build_evidence_bundle,
    clean_text,
    dedupe_preserve_order,
    truncate_text,
)


def _complete_canonical() -> CanonicalDodDocument:
    return CanonicalDodDocument(
        build_id=5,
        organization="org",
        project="proj",
        generated_at=datetime(2026, 5, 2, tzinfo=UTC),
        source_raw_bundle_path="data/raw/5/raw_bundle.json",
        run_context=RunContext(
            build_id=5,
            build_number="2026.05.02.1",
            pipeline_name="DoD Pipeline",
            repository_name="ado-dod-agent",
            source_branch="refs/heads/main",
            source_version="abc123",
            requested_by="alice",
            status="completed",
            result="succeeded",
        ),
        change_context=ChangeContext(
            work_items=[
                CanonicalWorkItem(
                    id=101,
                    type="User Story",
                    title="Add config rollout toggle",
                    description="<p>Implement   config update</p>",
                    acceptance_criteria="Flag can be toggled in lower env",
                    state="Done",
                    priority=1,
                    business_value=8,
                    tags=["api", "config"],
                    source_ref="raw.work_items.value[0]",
                )
            ],
            commits=[
                CanonicalCommit(
                    id="c1",
                    message="Add appsettings configuration for rollout",
                    author_name="dev",
                    authored_at=datetime(2026, 5, 2, tzinfo=UTC),
                    source_ref="raw.changes.value[0]",
                )
            ],
            pull_requests=[
                CanonicalPullRequest(
                    id=88,
                    title="Feature flag + config update",
                    description="Implements new behavior with safe rollout",
                    status="completed",
                    reviewers=["rev1"],
                    commit_ids=["c1"],
                    source_ref="raw.pull_requests.value[0]",
                )
            ],
            change_summary_signals=["Add rollout feature flag", "Add config update"],
        ),
        execution_context=ExecutionContext(
            stages=[
                CanonicalStage(
                    id="s1",
                    name="Deploy Stage",
                    result="succeeded",
                    state="completed",
                    duration_seconds=120.0,
                    source_ref="raw.timeline.records[0]",
                )
            ],
            jobs=[
                CanonicalJob(
                    id="j1",
                    name="Build Job",
                    result="succeeded",
                    state="completed",
                    duration_seconds=90.0,
                    source_ref="raw.timeline.records[1]",
                )
            ],
            tasks=[
                CanonicalTask(
                    id="t1",
                    name="Run unit tests",
                    type="Task",
                    result="failed",
                    state="completed",
                    duration_seconds=30.0,
                    source_ref="raw.timeline.records[2]",
                ),
                CanonicalTask(
                    id="t2",
                    name="Deploy to lower environment",
                    type="Task",
                    result="succeeded",
                    state="completed",
                    duration_seconds=20.0,
                    source_ref="raw.timeline.records[3]",
                ),
            ],
            artifacts=[
                CanonicalArtifact(
                    name="drop",
                    type="container",
                    resource_type="Container",
                    source_ref="raw.artifacts.value[0]",
                )
            ],
            deployment_signals=["Deploy to lower environment"],
            implementation_signals=["Build Job", "drop"],
            validation_signals=["Run unit tests"],
        ),
        quality_context=QualityContext(
            test_runs=[
                CanonicalTestRun(
                    id=1,
                    name="Unit Tests",
                    total_tests=10,
                    passed_tests=8,
                    failed_tests=1,
                    skipped_tests=1,
                )
            ],
            test_summary=CanonicalTestSummary(
                total_runs=1,
                total_tests=10,
                passed_tests=8,
                failed_tests=1,
                skipped_tests=1,
                pass_rate=0.8,
            ),
            failed_tests=[
                CanonicalTestResult(
                    id=99,
                    test_run_id=1,
                    test_name="test_database_migration",
                    outcome="Failed",
                    error_message="AssertionError",
                    source_ref="raw.test_results.value[0]",
                )
            ],
            warning_tests=[
                CanonicalTestResult(
                    id=100,
                    test_run_id=1,
                    test_name="test_optional_case",
                    outcome="Skipped",
                )
            ],
            quality_signals=["failed_tests=1"],
        ),
        risk_context=RiskContext(
            impacted_components=["Orders.API"],
            config_change_detected=True,
            database_change_detected=True,
            infrastructure_change_detected=True,
            dependency_change_detected=True,
            feature_flag_change_detected=True,
            rollback_indicators=["abc123", "drop"],
            risk_signals=["raw_collection_partial", "failed_tests=1"],
        ),
        normalization_metadata=NormalizationMetadata(
            raw_collection_status="partial",
            warnings=["some_raw_sections_missing"],
        ),
    )


def _partial_canonical() -> CanonicalDodDocument:
    return CanonicalDodDocument(
        build_id=9,
        organization="org",
        project="proj",
        generated_at=datetime(2026, 5, 2, tzinfo=UTC),
        run_context=RunContext(build_id=9),
        change_context=ChangeContext(
            commits=[CanonicalCommit(id="c1", message="")],
            missing_change_context=["pull_requests_missing_or_not_associated"],
        ),
        execution_context=ExecutionContext(
            missing_execution_context=["timeline_records_missing", "artifacts_missing"],
        ),
        quality_context=QualityContext(
            test_summary=CanonicalTestSummary(),
            missing_quality_context=["test_runs_missing", "test_results_missing"],
        ),
        risk_context=RiskContext(missing_risk_context=["insufficient_change_execution_text"]),
        normalization_metadata=NormalizationMetadata(),
    )


def test_evidence_bundle_builds_from_complete_canonical() -> None:
    bundle = build_evidence_bundle(
        _complete_canonical(),
        source_path="data/normalized/5/canonical.json",
    )
    assert bundle.build_id == 5
    assert bundle.bucket_1.work_item_evidence
    assert bundle.bucket_2.stage_evidence
    assert bundle.bucket_3.artifact_evidence


def test_evidence_bundle_builds_from_partial_canonical() -> None:
    bundle = build_evidence_bundle(_partial_canonical())
    assert bundle.build_id == 9
    assert bundle.bucket_1.evidence_gaps
    assert bundle.bucket_2.evidence_gaps
    assert bundle.bucket_3.evidence_gaps


def test_bucket_1_includes_work_items_commits_and_prs() -> None:
    bucket = build_evidence_bundle(_complete_canonical()).bucket_1
    assert len(bucket.work_item_evidence) == 1
    assert len(bucket.commit_evidence) == 1
    assert len(bucket.pull_request_evidence) == 1


def test_bucket_1_records_gap_when_prs_missing() -> None:
    canonical = _complete_canonical()
    canonical.change_context.pull_requests = []
    bucket = build_evidence_bundle(canonical).bucket_1
    assert "no PR metadata found" in bucket.evidence_gaps


def test_bucket_2_includes_timeline_artifacts_and_test_summary() -> None:
    bucket = build_evidence_bundle(_complete_canonical()).bucket_2
    assert bucket.stage_evidence
    assert bucket.job_evidence
    assert bucket.task_evidence
    assert bucket.artifact_evidence
    assert bucket.test_evidence.total_runs == 1


def test_bucket_2_records_gap_when_tests_missing() -> None:
    bucket = build_evidence_bundle(_partial_canonical()).bucket_2
    assert "no test results found" in bucket.evidence_gaps


def test_bucket_3_includes_artifacts_rollback_flags_and_signals() -> None:
    bucket = build_evidence_bundle(_complete_canonical()).bucket_3
    assert bucket.artifact_evidence
    assert bucket.rollback_indicators
    assert bucket.risk_flags.config_change_detected is True
    assert bucket.risk_flags.database_change_detected is True
    assert bucket.risk_flags.infrastructure_change_detected is True
    assert bucket.risk_flags.dependency_change_detected is True
    assert bucket.risk_flags.feature_flag_change_detected is True
    assert bucket.risk_signals


def test_failed_timeline_and_test_evidence_appear_in_bucket_3() -> None:
    bucket = build_evidence_bundle(_complete_canonical()).bucket_3
    source_types = {item.source_type for item in bucket.failed_or_warning_evidence}
    assert "timeline_task" in source_types
    assert "failed_test" in source_types


def test_text_cleanup_and_html_stripping() -> None:
    cleaned = clean_text("  <p>Hello   world</p>  ")
    assert cleaned == "Hello world"


def test_truncation_applied_for_long_description() -> None:
    canonical = _complete_canonical()
    canonical.change_context.work_items[0].description = "x" * 5000
    bundle = build_evidence_bundle(canonical, max_items_per_section=1)
    bucket = bundle.bucket_1
    assert bucket.work_item_evidence[0].description is not None
    assert len(bucket.work_item_evidence[0].description or "") <= 1200
    assert truncate_text("abcd", 3) == "abc"
    assert bundle.generation_metadata.max_items_per_section == 1


def test_dedupe_preserve_order_keeps_first_occurrence_order() -> None:
    values = dedupe_preserve_order(["a", "b", "a", "c", "b"])
    assert values == ["a", "b", "c"]
