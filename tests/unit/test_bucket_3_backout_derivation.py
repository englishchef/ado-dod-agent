"""Focused tests for activity-independent timing and recursive backout derivation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.app.models.canonical import (
    CanonicalDodDocument,
    CanonicalJob,
    CanonicalStage,
    CanonicalTask,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)
from backend.app.services.evidence.bucket_3_selection import classify_deployment_action
from backend.app.services.evidence.builder import (
    _container_activity_items,
    build_evidence_bundle,
)
from backend.app.services.validation.output_repair import repair_bucket_3_fields
from backend.app.services.validation.output_validator import validate_bucket_3_fields


def _canonical(
    stages: list[CanonicalStage],
    jobs: list[CanonicalJob] | None = None,
    tasks: list[CanonicalTask] | None = None,
) -> CanonicalDodDocument:
    return CanonicalDodDocument(
        build_id=5,
        organization="org",
        project="contact-center",
        generated_at=datetime(2026, 7, 17, tzinfo=UTC),
        run_context=RunContext(build_id=5, repository_name="contact-center-asac"),
        change_context=ChangeContext(),
        execution_context=ExecutionContext(
            stages=stages,
            jobs=jobs or [],
            tasks=tasks or [],
        ),
        quality_context=QualityContext(),
        risk_context=RiskContext(),
        normalization_metadata=NormalizationMetadata(),
    )


def _stage(
    stage_id: str,
    name: str,
    *,
    offset_seconds: float = 0,
    duration_seconds: float = 5213.573333,
    result: str = "succeeded",
) -> CanonicalStage:
    start = datetime(2026, 6, 26, 22, 8, 45, 80000, tzinfo=UTC) + timedelta(
        seconds=offset_seconds
    )
    return CanonicalStage(
        id=stage_id,
        name=name,
        state="completed",
        result=result,
        start_time=start,
        finish_time=start + timedelta(seconds=duration_seconds),
        duration_seconds=duration_seconds,
    )


def _backout(bucket: object) -> str:
    evidence = {"bucket_3": bucket.model_dump(mode="json")}  # type: ignore[attr-defined]
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": "Restore the change.",
            "risk_impact_analysis": "No planned impact is expected. There is a possible risk.",
        },
        evidence,
        fields_to_repair={"backout_plan"},
    )
    return str(repaired["backout_plan"])


def test_valid_uat_without_deployment_activities_is_selected_for_full_duration() -> None:
    bucket = build_evidence_bundle(_canonical([_stage("uat", "UAT")])).bucket_3

    assert bucket.backout_time_derivation.selected_environment == "UAT"
    assert bucket.backout_time_derivation.source_duration_seconds == 5213.573333
    assert bucket.backout_time_derivation.final_estimate_minutes == 90
    assert bucket.environment_candidates[0].selected is True
    assert bucket.environment_candidates[0].deployment_activities == []
    assert not any("deployment activity" in item.reason for item in bucket.rejected_stages)
    assert bucket.backout_step_derivation.fallback_used is True
    assert "approximately 1 hour 30 minutes" in _backout(bucket)


def test_uat_wins_over_qa_without_using_activity_discovery_for_selection() -> None:
    bucket = build_evidence_bundle(
        _canonical([_stage("qa", "QA"), _stage("uat", "UAT", offset_seconds=20)])
    ).bucket_3

    assert bucket.backout_time_derivation.selected_environment == "UAT"
    assert any(item.stage_name == "QA" for item in bucket.rejected_stages)


def test_recursive_traversal_discovers_nested_actions_with_depth_and_ancestry() -> None:
    canonical = _canonical(
        [_stage("uat", "UAT")],
        jobs=[
            CanonicalJob(id="direct", parent_id="uat", name="Solution Deployment"),
            CanonicalJob(id="nested", parent_id="direct", name="Nested Deployment Job"),
        ],
        tasks=[
            CanonicalTask(
                id="upgrade",
                parent_id="nested",
                name="Upgrade Solution",
                state="completed",
                result="succeeded",
            ),
            CanonicalTask(
                id="apply",
                parent_id="nested",
                name="Apply Solution Upgrade",
                state="completed",
                result="succeeded",
            ),
        ],
    )

    bucket = build_evidence_bundle(canonical).bucket_3
    derivation = bucket.backout_step_derivation

    assert [item.raw_name for item in derivation.source_tasks][-2:] == [
        "Upgrade Solution",
        "Apply Solution Upgrade",
    ]
    assert all(item.depth == 3 for item in derivation.source_tasks[-2:])
    assert derivation.source_tasks[-1].ancestor_names == [
        "UAT",
        "Solution Deployment",
        "Nested Deployment Job",
    ]
    assert derivation.max_depth == 3
    assert derivation.normalized_actions.count("solution_upgrade") == 1
    assert _backout(bucket).count("complete the solution rollback") == 1


def test_recursive_traversal_prevents_cycles() -> None:
    canonical = _canonical(
        [_stage("uat", "UAT")],
        jobs=[
            CanonicalJob(id="job-a", parent_id="uat", name="Direct Job"),
            CanonicalJob(id="uat", parent_id="job-a", name="Cycle Back to Stage"),
        ],
    )

    descendants = _container_activity_items(
        canonical,
        canonical.execution_context.stages[0],
        "stage",
    )

    assert [item.item.name for item in descendants] == ["Direct Job"]


def test_classification_uses_negative_patterns_and_multiple_signals() -> None:
    assert classify_deployment_action(name="Get Base Solution Versions").classification == (
        "metadata_lookup"
    )
    assert classify_deployment_action(name="Apply Solution Upgrade").classification == (
        "solution_upgrade"
    )
    assert classify_deployment_action(name="Upgrade Solution").classification == (
        "solution_upgrade"
    )
    assert classify_deployment_action(name="Power Platform Import Solution").classification == (
        "solution_deployment"
    )
    assert classify_deployment_action(name="Validate Connection").classification == "preparation"
    assert classify_deployment_action(name="Deploy_03").classification == "unknown"
    assert classify_deployment_action(
        name="Deploy_03",
        task_type="Power Platform Import Solution",
    ).classification == "solution_deployment"
    assert classify_deployment_action(
        name="Task_07",
        command="pac solution upgrade",
    ).classification == "solution_upgrade"


def test_cryptic_nested_tasks_use_metadata_and_persist_classification_evidence() -> None:
    bucket = build_evidence_bundle(
        _canonical(
            [_stage("uat", "UAT")],
            jobs=[CanonicalJob(id="job", parent_id="uat", name="Deployment Job")],
            tasks=[
                CanonicalTask(
                    id="deploy",
                    parent_id="job",
                    name="Deploy_03",
                    type="Task",
                    task_definition="Power Platform Import Solution",
                    command="pac solution import",
                    state="completed",
                    result="succeeded",
                ),
                CanonicalTask(
                    id="upgrade",
                    parent_id="job",
                    name="Task_07",
                    type="Task",
                    command="pac solution upgrade",
                    state="completed",
                    result="succeeded",
                ),
            ],
        )
    ).bucket_3

    by_id = {item.record_id: item for item in bucket.backout_step_derivation.source_tasks}

    assert by_id["deploy"].detected_action == "solution_deployment"
    assert by_id["deploy"].classification_evidence == ["task_definition"]
    assert by_id["upgrade"].detected_action == "solution_upgrade"
    assert by_id["upgrade"].classification_evidence == ["command"]


def test_generic_fallback_does_not_invent_technical_actions() -> None:
    bucket = build_evidence_bundle(
        _canonical(
            [_stage("uat", "UAT")],
            tasks=[
                CanonicalTask(
                    id="cryptic",
                    parent_id="uat",
                    name="Task_07",
                    state="completed",
                    result="succeeded",
                )
            ],
        )
    ).bucket_3

    backout = _backout(bucket)

    assert bucket.backout_step_derivation.fallback_used is True
    assert "Restore the previously validated version" in backout
    assert "configuration" not in backout.lower()
    assert "database" not in backout.lower()
    assert "infrastructure" not in backout.lower()
    assert "restart" not in backout.lower()


def test_unsupported_step_and_raw_metadata_are_flagged_and_removed() -> None:
    bucket = build_evidence_bundle(
        _canonical(
            [_stage("uat", "UAT")],
            tasks=[
                CanonicalTask(
                    id="deploy",
                    parent_id="uat",
                    name="Import Solution",
                    state="completed",
                    result="succeeded",
                )
            ],
        )
    ).bucket_3
    evidence = {"bucket_3": bucket.model_dump(mode="json")}
    generated = (
        "1. Stop or pause the production deployment.\n"
        "2. Run pac solution import from C:\\drop\\solution.zip using task "
        "123e4567-e89b-42d3-a456-426614174000.\n"
        "3. Execute a database rollback through https://example.invalid/run.\n"
        "4. Validate application health.\n\n"
        "Estimated backout time: approximately 1 hour 30 minutes."
    )

    issues = validate_bucket_3_fields(
        {
            "backout_plan": generated,
            "risk_impact_analysis": (
                "No planned impact is expected for the application. "
                "There is a possible risk of temporary disruption."
            ),
        },
        evidence,
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": generated,
            "risk_impact_analysis": "No planned impact is expected.",
        },
        evidence,
        fields_to_repair={"backout_plan"},
    )
    codes = {issue.code for issue in issues}
    repaired_backout = str(repaired["backout_plan"])

    assert "BACKOUT_UNSUPPORTED_STEP" in codes
    assert "BACKOUT_STEP_RAW_METADATA_LEAKAGE" in codes
    assert "database" not in repaired_backout.lower()
    assert "pac solution" not in repaired_backout.lower()
    assert "123e4567" not in repaired_backout
    assert "http" not in repaired_backout.lower()


def test_validator_flags_legacy_empty_activity_rejection_and_incomplete_traversal() -> None:
    evidence = {
        "bucket_3": {
            "backout_time_derivation": {
                "calculation_method": "lower_environment_stage_duration",
                "selected_environment": "QA",
                "selected_stage_name": "QA",
                "stage_start_time": "2026-06-26T22:00:00Z",
                "stage_finish_time": "2026-06-26T22:10:00Z",
                "source_duration_seconds": 600,
                "final_estimate_minutes": 10,
            },
            "environment_candidates": [
                {
                    "stage_name": "UAT",
                    "normalized_environment": "UAT",
                    "state": "completed",
                    "result": "succeeded",
                    "start_time": "2026-06-26T22:00:00Z",
                    "finish_time": "2026-06-26T23:00:00Z",
                    "duration_seconds": 3600,
                    "deployment_activities": [],
                    "selected": False,
                }
            ],
            "rejected_stages": [
                {
                    "stage_name": "UAT",
                    "reason": (
                        "Stage does not contain a valid application or solution deployment "
                        "activity."
                    ),
                }
            ],
            "backout_step_derivation": {
                "recursive_traversal_used": False,
                "traversal_complete": False,
                "fallback_used": True,
                "ignored_tasks": [],
            },
        }
    }
    issues = validate_bucket_3_fields(
        {
            "backout_plan": (
                "1. Stop or pause the production deployment.\n"
                "2. Restore the previously validated application.\n"
                "3. Validate application health.\n\n"
                "Estimated backout time: approximately 1 hour."
            ),
            "risk_impact_analysis": (
                "No planned impact is expected for the application. "
                "There is a possible risk of temporary disruption."
            ),
        },
        evidence,
        "bucket_3",
    )
    codes = {issue.code for issue in issues}

    assert "LOWER_ENVIRONMENT_STAGE_REJECTED_FOR_EMPTY_ACTIVITIES" in codes
    assert "BACKOUT_RECURSIVE_TRAVERSAL_INCOMPLETE" in codes
    assert "BACKOUT_GENERIC_FALLBACK_USED" in codes
