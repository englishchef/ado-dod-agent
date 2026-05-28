"""Tests for Phase 7B evidence quality routing."""

from __future__ import annotations

from backend.app.services.routing.evidence_quality import assess_evidence_quality


def test_bucket_1_strong_when_work_items_and_commits_exist() -> None:
    result = assess_evidence_quality(
        {
            "bucket_1": {
                "work_item_evidence": [{"title": "Feature", "description": "Add feature"}],
                "commit_evidence": [{"message": "implement feature"}],
                "pull_request_evidence": [],
            }
        }
    )

    assert result.bucket_1_quality == "strong"


def test_bucket_1_medium_when_only_commits_exist() -> None:
    result = assess_evidence_quality({"bucket_1": {"commit_evidence": [{"message": "fix"}]}})

    assert result.bucket_1_quality == "medium"


def test_bucket_1_missing_pr_alone_does_not_make_weak() -> None:
    result = assess_evidence_quality(
        {
            "bucket_1": {
                "work_item_evidence": [{"title": "Feature"}],
                "commit_evidence": [{"message": "fix"}],
                "pull_request_evidence": [],
            }
        }
    )

    assert result.bucket_1_quality == "strong"


def test_bucket_2_weak_when_tests_and_validation_signals_missing() -> None:
    result = assess_evidence_quality(
        {"bucket_2": {"test_evidence": {"total_tests": 0}, "validation_signals": []}}
    )

    assert result.bucket_2_quality == "weak"


def test_bucket_2_medium_when_pipeline_exists_but_tests_missing() -> None:
    result = assess_evidence_quality(
        {
            "bucket_2": {
                "stage_evidence": [{"name": "Deploy"}],
                "task_evidence": [{"name": "Validate"}],
                "test_evidence": {"total_tests": 0},
                "validation_signals": ["Validate"],
                "deployment_signals": ["Deploy"],
            }
        }
    )

    assert result.bucket_2_quality == "medium"


def test_bucket_3_weak_when_no_artifacts_or_rollback_indicators() -> None:
    result = assess_evidence_quality({"bucket_3": {"artifact_evidence": []}})

    assert result.bucket_3_quality == "weak"


def test_bucket_3_strong_when_artifacts_source_version_and_rollback_exist() -> None:
    result = assess_evidence_quality(
        {
            "bucket_3": {
                "service_context": {"source_version": "abc"},
                "artifact_evidence": [{"name": "drop"}],
                "rollback_indicators": ["abc"],
                "risk_flags": {"config_change_detected": True},
            }
        }
    )

    assert result.bucket_3_quality == "strong"
