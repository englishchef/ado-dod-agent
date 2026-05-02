"""Tests for deterministic canonical normalizer."""

from __future__ import annotations

from typing import Any

from backend.app.services.normalizers.canonical import normalize_raw_bundle


def _build_complete_raw_bundle() -> dict[str, Any]:
    return {
        "build_id": 77,
        "organization": "org",
        "project": "proj",
        "status": "partial",
        "errors": [{"collector": "quality_context", "message": "permission denied"}],
        "raw": {
            "build": {
                "id": 77,
                "buildNumber": "20260502.1",
                "definition": {"id": 5, "name": "Pipeline"},
                "repository": {"id": "repo-1", "name": "repo", "type": "TfsGit"},
                "sourceBranch": "refs/heads/main",
                "sourceVersion": "abcdef12345",
                "requestedBy": {"displayName": "User One"},
                "requestedFor": {"uniqueName": "user@example.com"},
                "queueTime": "2026-05-01T10:00:00Z",
                "startTime": "2026-05-01T10:01:00Z",
                "finishTime": "2026-05-01T10:30:00Z",
                "status": "completed",
                "result": "succeeded",
                "reason": "manual",
                "url": "https://dev.azure.com/build/77",
                "_links": {"web": {"href": "https://dev.azure.com/web/77"}},
            },
            "timeline": {
                "records": [
                    {
                        "id": "stage-1",
                        "name": "Deploy to Prod",
                        "type": "Stage",
                        "state": "completed",
                        "result": "succeeded",
                        "startTime": "2026-05-01T10:10:00Z",
                        "finishTime": "2026-05-01T10:20:00Z",
                    },
                    {
                        "id": "job-1",
                        "name": "Build Job",
                        "type": "Job",
                        "parentId": "stage-1",
                        "state": "completed",
                        "result": "succeeded",
                        "startTime": "2026-05-01T10:11:00Z",
                        "finishTime": "2026-05-01T10:19:00Z",
                    },
                    {
                        "id": "task-1",
                        "name": "Run tests",
                        "type": "Task",
                        "parentId": "job-1",
                        "state": "completed",
                        "result": "failed",
                        "startTime": "2026-05-01T10:12:00Z",
                        "finishTime": "2026-05-01T10:13:00Z",
                        "log": {"url": "https://dev.azure.com/log/1"},
                    },
                ]
            },
            "artifacts": {
                "value": [
                    {
                        "name": "drop",
                        "type": "container",
                        "resource": {"type": "pipeline", "downloadUrl": "https://download"},
                    }
                ]
            },
            "work_items": {
                "value": [
                    {
                        "id": 1001,
                        "url": "https://dev.azure.com/wit/1001",
                        "fields": {
                            "System.Id": 1001,
                            "System.WorkItemType": "User Story",
                            "System.Title": "Update config and db migration",
                            "System.State": "Done",
                            "System.Reason": "Completed",
                            "System.AssignedTo": {"displayName": "Assignee"},
                            "System.CreatedBy": {"uniqueName": "creator@ex.com"},
                            "System.ChangedBy": "changer@ex.com",
                            "System.AreaPath": "Payments",
                            "System.IterationPath": "Sprint 1",
                            "System.Tags": "one; two ; three",
                            "System.Description": "Uses feature flag and terraform",
                            "Microsoft.VSTS.Common.AcceptanceCriteria": "must pass",
                            "Microsoft.VSTS.Common.Priority": "2",
                            "Microsoft.VSTS.Common.BusinessValue": 9,
                        },
                    }
                ]
            },
            "changes": {
                "value": [
                    {
                        "id": "commit-1",
                        "message": "update pyproject dependency and appsettings json",
                        "author": {"displayName": "Author", "uniqueName": "a@b.com"},
                        "timestamp": "2026-05-01T09:55:00Z",
                        "location": "https://dev.azure.com/commit-1",
                    }
                ]
            },
            "pull_requests": {
                "pull_requests": [
                    {
                        "pullRequestId": 12,
                        "title": "Feature flag rollout",
                        "description": "kubernetes infra update",
                        "status": "completed",
                        "createdBy": {"displayName": "PR Owner"},
                        "sourceRefName": "refs/heads/feature",
                        "targetRefName": "refs/heads/main",
                        "mergeStatus": "succeeded",
                        "isDraft": False,
                        "reviewers": [{"displayName": "Reviewer 1"}],
                        "url": "https://dev.azure.com/pr/12",
                        "lastMergeSourceCommit": {"commitId": "commit-1"},
                    }
                ],
                "commits": {"12": {"value": [{"commitId": "commit-1"}]}},
            },
            "test_runs": {
                "value": [
                    {
                        "id": 9,
                        "name": "Unit Tests",
                        "state": "completed",
                        "outcome": "Failed",
                        "totalTests": 3,
                        "passedTests": 1,
                        "failedTests": 1,
                        "skippedTests": 1,
                    }
                ]
            },
            "test_results": {
                "value": [
                    {
                        "run_id": 9,
                        "payload": {
                            "value": [
                                {"id": 1, "testCaseTitle": "test_passed", "outcome": "Passed"},
                                {"id": 2, "testCaseTitle": "test_failed", "outcome": "Failed"},
                                {"id": 3, "testCaseTitle": "test_skipped", "outcome": "Skipped"},
                            ]
                        },
                    }
                ]
            },
        },
    }


def _bundle_with_message(message: str) -> dict[str, Any]:
    bundle = _build_complete_raw_bundle()
    bundle["raw"]["changes"]["value"][0]["message"] = message
    return bundle


def test_complete_raw_bundle_normalizes_successfully() -> None:
    document = normalize_raw_bundle(_build_complete_raw_bundle())
    assert document.build_id == 77
    assert document.run_context.pipeline_name == "Pipeline"
    assert len(document.change_context.work_items) == 1
    assert len(document.change_context.commits) == 1
    assert len(document.change_context.pull_requests) == 1
    assert len(document.execution_context.stages) == 1
    assert len(document.execution_context.jobs) == 1
    assert len(document.execution_context.tasks) == 1
    assert len(document.execution_context.artifacts) == 1
    assert len(document.quality_context.test_runs) == 1
    assert len(document.quality_context.failed_tests) == 1
    assert len(document.quality_context.warning_tests) == 1


def test_partial_raw_bundle_normalizes_successfully() -> None:
    bundle = {
        "build_id": 10,
        "organization": "org",
        "project": "proj",
        "status": "partial",
        "raw": {},
    }
    document = normalize_raw_bundle(bundle)
    assert document.build_id == 10
    assert document.normalization_metadata.raw_collection_status == "partial"
    assert "some_raw_sections_missing" in document.normalization_metadata.warnings


def test_missing_work_items_does_not_fail() -> None:
    bundle = _build_complete_raw_bundle()
    bundle["raw"]["work_items"] = {"value": []}
    document = normalize_raw_bundle(bundle)
    assert document.change_context.work_items == []
    assert "work_items_missing" in document.change_context.missing_change_context


def test_missing_tests_does_not_fail() -> None:
    bundle = _build_complete_raw_bundle()
    bundle["raw"]["test_runs"] = {"value": []}
    bundle["raw"]["test_results"] = {"value": []}
    document = normalize_raw_bundle(bundle)
    assert document.quality_context.test_summary.total_runs == 0
    assert "test_runs_missing" in document.quality_context.missing_quality_context


def test_timeline_classification_into_stages_jobs_tasks() -> None:
    document = normalize_raw_bundle(_build_complete_raw_bundle())
    assert document.execution_context.stages[0].name == "Deploy to Prod"
    assert document.execution_context.jobs[0].name == "Build Job"
    assert document.execution_context.tasks[0].name == "Run tests"


def test_work_item_field_mapping_identity_and_tags() -> None:
    document = normalize_raw_bundle(_build_complete_raw_bundle())
    work_item = document.change_context.work_items[0]
    assert work_item.id == 1001
    assert work_item.title == "Update config and db migration"
    assert work_item.assigned_to == "Assignee"
    assert work_item.created_by == "creator@ex.com"
    assert work_item.changed_by == "changer@ex.com"
    assert work_item.tags == ["one", "two", "three"]


def test_test_summary_pass_rate_calculates() -> None:
    document = normalize_raw_bundle(_build_complete_raw_bundle())
    summary = document.quality_context.test_summary
    assert summary.total_tests == 3
    assert summary.passed_tests == 1
    assert summary.failed_tests >= 1
    assert summary.pass_rate == 0.3333


def test_risk_heuristic_detects_config_changes() -> None:
    document = normalize_raw_bundle(_bundle_with_message("update appsettings config yaml"))
    assert document.risk_context.config_change_detected is True


def test_risk_heuristic_detects_database_changes() -> None:
    document = normalize_raw_bundle(_bundle_with_message("apply sql migration schema change"))
    assert document.risk_context.database_change_detected is True


def test_risk_heuristic_detects_infrastructure_changes() -> None:
    document = normalize_raw_bundle(_bundle_with_message("terraform kubernetes infra update"))
    assert document.risk_context.infrastructure_change_detected is True


def test_risk_heuristic_detects_dependency_changes() -> None:
    document = normalize_raw_bundle(
        _bundle_with_message("update dependency in pyproject and requirements")
    )
    assert document.risk_context.dependency_change_detected is True


def test_risk_heuristic_detects_feature_flag_changes() -> None:
    document = normalize_raw_bundle(_bundle_with_message("enable feature flag for rollout"))
    assert document.risk_context.feature_flag_change_detected is True
