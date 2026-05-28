"""Evidence quality assessment for Phase 7B routing."""

from __future__ import annotations

from typing import Any

from backend.app.models.routing import EvidenceQualityAssessment


def assess_evidence_quality(evidence_bundle: dict[str, Any]) -> EvidenceQualityAssessment:
    """Assess prompt evidence quality for each deterministic bucket."""

    bucket_1 = _as_dict(evidence_bundle.get("bucket_1"))
    bucket_2 = _as_dict(evidence_bundle.get("bucket_2"))
    bucket_3 = _as_dict(evidence_bundle.get("bucket_3"))

    bucket_1_quality, bucket_1_reasons = _assess_bucket_1(bucket_1)
    bucket_2_quality, bucket_2_reasons = _assess_bucket_2(bucket_2)
    bucket_3_quality, bucket_3_reasons = _assess_bucket_3(bucket_3)

    return EvidenceQualityAssessment(
        bucket_1_quality=bucket_1_quality,  # type: ignore[arg-type]
        bucket_2_quality=bucket_2_quality,  # type: ignore[arg-type]
        bucket_3_quality=bucket_3_quality,  # type: ignore[arg-type]
        bucket_1_reasons=bucket_1_reasons,
        bucket_2_reasons=bucket_2_reasons,
        bucket_3_reasons=bucket_3_reasons,
    )


def _assess_bucket_1(bucket: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    work_items = _as_list(bucket.get("work_item_evidence"))
    commits = _as_list(bucket.get("commit_evidence"))
    pull_requests = _as_list(bucket.get("pull_request_evidence"))
    meaningful_work_items = [
        item
        for item in work_items
        if _has_any_text(_as_dict(item), ("title", "description", "acceptance_criteria"))
    ]
    meaningful_commits = [
        item for item in commits if _has_any_text(_as_dict(item), ("message", "id"))
    ]

    if work_items:
        reasons.append("Work item evidence is available.")
    if meaningful_work_items:
        reasons.append(
            "At least one work item includes title, description, or acceptance criteria."
        )
    if meaningful_commits:
        reasons.append("Commit evidence is available.")
    if not pull_requests:
        reasons.append("PR evidence is missing, but PR evidence is optional.")

    if work_items and meaningful_commits and meaningful_work_items:
        return "strong", reasons
    if work_items or meaningful_commits:
        reasons.append("Change intent evidence is present but descriptive context is limited.")
        return "medium", reasons
    reasons.append("No work item evidence or meaningful commit evidence is available.")
    return "weak", reasons


def _assess_bucket_2(bucket: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    stages = _as_list(bucket.get("stage_evidence"))
    jobs = _as_list(bucket.get("job_evidence"))
    tasks = _as_list(bucket.get("task_evidence"))
    artifacts = _as_list(bucket.get("artifact_evidence"))
    test_evidence = _as_dict(bucket.get("test_evidence"))
    total_tests = _as_int(test_evidence.get("total_tests"))
    validation_signals = _as_list(bucket.get("validation_signals"))
    deployment_signals = _as_list(bucket.get("deployment_signals"))
    quality_signals = _as_list(bucket.get("quality_signals"))
    has_stage_or_task = bool(stages or jobs or tasks)
    has_tests_or_quality = bool((total_tests or 0) > 0 or quality_signals)

    if has_stage_or_task:
        reasons.append("Stage, job, or task evidence is available.")
    if artifacts:
        reasons.append("Artifact evidence is available.")
    if (total_tests or 0) > 0:
        reasons.append("Collected test results are available.")
    elif quality_signals:
        reasons.append("Quality signals are available even though test results are missing.")
    else:
        reasons.append("Collected test results are missing.")

    if has_stage_or_task and artifacts and has_tests_or_quality:
        return "strong", reasons
    if has_stage_or_task and (validation_signals or deployment_signals):
        reasons.append("Pipeline signals are available, but test evidence is limited or missing.")
        return "medium", reasons
    reasons.append("Validation/deployment signals are weak or missing.")
    return "weak", reasons


def _assess_bucket_3(bucket: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    service_context = _as_dict(bucket.get("service_context"))
    artifacts = _as_list(bucket.get("artifact_evidence"))
    rollback_indicators = _as_list(bucket.get("rollback_indicators"))
    impacted_components = _as_list(bucket.get("impacted_components"))
    risk_signals = _as_list(bucket.get("risk_signals"))
    risk_flags = _as_dict(bucket.get("risk_flags"))
    source_version = _as_str(service_context.get("source_version"))
    has_risk_flags = any(value is True for value in risk_flags.values())

    if artifacts:
        reasons.append("Artifact evidence is available.")
    if rollback_indicators:
        reasons.append("Rollback indicators are available.")
    if source_version:
        reasons.append("Source version is available.")
    if risk_signals or has_risk_flags:
        reasons.append("Risk signals or risk flags are present.")

    if artifacts and rollback_indicators and source_version and (risk_signals or has_risk_flags):
        return "strong", reasons
    if source_version and (artifacts or rollback_indicators):
        reasons.append("Rollback/risk evidence is partially available.")
        return "medium", reasons
    if not artifacts:
        reasons.append("Artifact evidence is missing.")
    if not rollback_indicators:
        reasons.append("Rollback indicators are missing.")
    if not impacted_components:
        reasons.append("Impacted components are not identified.")
    if not risk_signals and not has_risk_flags:
        reasons.append("No configured risk signal was detected in the evidence.")
    return "weak", reasons


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _has_any_text(payload: dict[str, Any], keys: tuple[str, ...]) -> bool:
    return any(_as_str(payload.get(key)) for key in keys)
