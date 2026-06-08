"""Deterministic evidence bucket generation from canonical documents."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from html import unescape
from typing import Any

from backend.app.models.canonical import (
    CanonicalArtifact,
    CanonicalCommit,
    CanonicalDodDocument,
    CanonicalJob,
    CanonicalPullRequest,
    CanonicalStage,
    CanonicalTask,
    CanonicalTestResult,
    CanonicalWorkItem,
)
from backend.app.models.evidence import (
    ArtifactEvidence,
    ChangeIntentEvidence,
    CommitEvidence,
    EvidenceBundle,
    EvidenceGenerationMetadata,
    EvidenceServiceContext,
    EvidenceSourceRef,
    ExecutionValidationEvidence,
    FailureWarningEvidence,
    JobEvidence,
    PullRequestEvidence,
    RiskFlagsEvidence,
    RollbackRiskEvidence,
    StageEvidence,
    TaskEvidence,
    TestEvidenceSummary,
    WorkItemEvidence,
)
from backend.app.services.evidence.reference_normalizer import normalize_source_ref

DEFAULT_MAX_ITEMS_PER_SECTION = 10
MAX_DESCRIPTION_CHARS = 1200
MAX_COMMIT_MESSAGE_CHARS = 500
MAX_SIGNAL_CHARS = 300

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_IMPLEMENTATION_HINTS = (
    "build",
    "scan",
    "deploy",
    "release",
    "test",
    "validate",
    "verify",
    "approval",
    "prod",
    "lower",
    "environment",
)
_DEPLOYMENT_HINTS = ("deploy", "release", "environment", "prod", "stage", "lower")


def clean_text(value: Any) -> str | None:
    """Normalize text by stripping HTML and collapsing whitespace."""

    if value is None:
        return None
    text = str(value)
    text = unescape(text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def truncate_text(value: str | None, max_chars: int) -> str | None:
    """Truncate text to max length while preserving readability."""

    if value is None:
        return None
    if len(value) <= max_chars:
        return value
    if max_chars <= 3:
        return value[:max_chars]
    return f"{value[: max_chars - 3].rstrip()}..."


def dedupe_preserve_order(values: list[str]) -> list[str]:
    """Dedupe list preserving first-seen order."""

    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def is_meaningful_text(value: str | None) -> bool:
    """Return whether text likely contains useful evidence."""

    if value is None:
        return False
    lowered = value.strip().lower()
    if not lowered:
        return False
    if lowered in {"n/a", "na", "none", "null", "{}", "[]", "-", "tbd"}:
        return False
    return len(lowered) >= 3


def _service_context(canonical: CanonicalDodDocument) -> EvidenceServiceContext:
    run = canonical.run_context
    return EvidenceServiceContext(
        build_id=canonical.build_id,
        build_number=run.build_number,
        pipeline_name=run.pipeline_name,
        repository_name=run.repository_name,
        source_branch=run.source_branch,
        source_version=run.source_version,
        result=run.result,
        status=run.status,
        requested_by=run.requested_by,
    )


def _contains_hint(name: str | None, hints: tuple[str, ...]) -> bool:
    lowered = (name or "").lower()
    return any(hint in lowered for hint in hints)


def _rank_work_item(item: CanonicalWorkItem) -> tuple[int, int]:
    score = 0
    if is_meaningful_text(clean_text(item.description)):
        score += 3
    if is_meaningful_text(clean_text(item.acceptance_criteria)):
        score += 3
    if item.priority is not None:
        score += 1
    if item.business_value is not None:
        score += 1
    if is_meaningful_text(clean_text(item.title)):
        score += 1
    return (score, item.id)


def _rank_pull_request(item: CanonicalPullRequest) -> tuple[int, int]:
    score = 0
    if is_meaningful_text(clean_text(item.title)):
        score += 2
    if is_meaningful_text(clean_text(item.description)):
        score += 2
    if is_meaningful_text(clean_text(item.status)):
        score += 1
    return (score, item.id)


def _rank_commit(item: CanonicalCommit) -> tuple[int, int]:
    score = 0
    message = clean_text(item.message)
    if is_meaningful_text(message):
        score += 2
    if is_meaningful_text(clean_text(item.author_name)):
        score += 1
    key = len(message or "")
    return (score, key)


def _rank_named_entity(name: str | None, result: str | None) -> int:
    score = 0
    if _contains_hint(name, _IMPLEMENTATION_HINTS):
        score += 2
    lowered_result = (result or "").lower()
    if lowered_result and lowered_result != "succeeded":
        score += 3
    return score


def _slice_with_tracking(items: list[Any], max_items: int) -> tuple[list[Any], bool]:
    if len(items) <= max_items:
        return items, False
    return items[:max_items], True


def _friendly_source_ref(
    source_type: str,
    item: Any,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> str:
    friendly_ref, map_entry = normalize_source_ref(
        source_type=source_type,
        item=item,
        original_ref=getattr(item, "source_ref", None),
    )
    if source_ref_map is not None:
        source_ref_map.setdefault(friendly_ref, map_entry)
    return friendly_ref


def build_bucket_1_change_intent(
    canonical: CanonicalDodDocument,
    max_items_per_section: int = DEFAULT_MAX_ITEMS_PER_SECTION,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> ChangeIntentEvidence:
    """Build evidence bucket for change intent fields."""

    work_items_sorted = sorted(
        canonical.change_context.work_items,
        key=_rank_work_item,
        reverse=True,
    )
    pull_requests_sorted = sorted(
        canonical.change_context.pull_requests,
        key=_rank_pull_request,
        reverse=True,
    )
    commits_sorted = sorted(
        canonical.change_context.commits,
        key=_rank_commit,
        reverse=True,
    )

    work_items, _ = _slice_with_tracking(work_items_sorted, max_items_per_section)
    pull_requests, _ = _slice_with_tracking(pull_requests_sorted, max_items_per_section)
    commits, _ = _slice_with_tracking(commits_sorted, max_items_per_section)

    work_item_evidence = [
        WorkItemEvidence(
            id=item.id,
            type=clean_text(item.type),
            title=truncate_text(clean_text(item.title), 300),
            state=clean_text(item.state),
            description=truncate_text(clean_text(item.description), MAX_DESCRIPTION_CHARS),
            acceptance_criteria=truncate_text(
                clean_text(item.acceptance_criteria),
                MAX_DESCRIPTION_CHARS,
            ),
            priority=item.priority,
            business_value=item.business_value,
            tags=item.tags[:20],
            source_ref=_friendly_source_ref("work_item", item, source_ref_map),
        )
        for item in work_items
    ]
    pr_evidence = [
        PullRequestEvidence(
            id=item.id,
            title=truncate_text(clean_text(item.title), 300),
            description=truncate_text(clean_text(item.description), MAX_DESCRIPTION_CHARS),
            status=clean_text(item.status),
            source_branch=clean_text(item.source_branch),
            target_branch=clean_text(item.target_branch),
            reviewers=item.reviewers[:max_items_per_section],
            commit_ids=item.commit_ids[:max_items_per_section],
            source_ref=_friendly_source_ref("pull_request", item, source_ref_map),
        )
        for item in pull_requests
    ]
    commit_evidence = []
    for item in commits:
        message = truncate_text(clean_text(item.message), MAX_COMMIT_MESSAGE_CHARS)
        if not is_meaningful_text(message):
            continue
        commit_evidence.append(
            CommitEvidence(
                id=item.id,
                message=message,
                author_name=clean_text(item.author_name),
                authored_at=item.authored_at,
                source_ref=_friendly_source_ref("commit", item, source_ref_map),
            )
        )

    gaps = list(canonical.change_context.missing_change_context)
    if not work_item_evidence:
        gaps.append("no work items found")
    if not pr_evidence:
        gaps.append("no PR metadata found")
    if not commit_evidence:
        gaps.append("no meaningful commit messages found")

    references = dedupe_preserve_order(
        [
            *(item.source_ref for item in work_item_evidence if item.source_ref),
            *(item.source_ref for item in pr_evidence if item.source_ref),
            *(item.source_ref for item in commit_evidence if item.source_ref),
        ]
    )
    signals = dedupe_preserve_order(
        [
            truncate_text(clean_text(signal), MAX_SIGNAL_CHARS) or ""
            for signal in canonical.change_context.change_summary_signals
            if is_meaningful_text(clean_text(signal))
        ]
    )
    signals = [signal for signal in signals if signal]

    return ChangeIntentEvidence(
        target_fields=["change_description", "short_change_description", "justification"],
        service_context=_service_context(canonical),
        work_item_evidence=work_item_evidence,
        commit_evidence=commit_evidence,
        pull_request_evidence=pr_evidence,
        change_summary_signals=signals,
        evidence_gaps=dedupe_preserve_order(gaps),
        evidence_references=references,
    )


def _select_ranked_stages(
    stages: list[CanonicalStage],
    max_items: int,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> tuple[list[StageEvidence], bool]:
    ranked = sorted(
        stages,
        key=lambda item: _rank_named_entity(item.name, item.result),
        reverse=True,
    )
    selected, truncated = _slice_with_tracking(ranked, max_items)
    return (
        [
            StageEvidence(
                name=truncate_text(clean_text(item.name), 240) or "unknown",
                result=clean_text(item.result),
                state=clean_text(item.state),
                duration_seconds=item.duration_seconds,
                source_ref=_friendly_source_ref("stage", item, source_ref_map),
            )
            for item in selected
        ],
        truncated,
    )


def _select_ranked_jobs(
    jobs: list[CanonicalJob],
    max_items: int,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> tuple[list[JobEvidence], bool]:
    ranked = sorted(
        jobs,
        key=lambda item: _rank_named_entity(item.name, item.result),
        reverse=True,
    )
    selected, truncated = _slice_with_tracking(ranked, max_items)
    return (
        [
            JobEvidence(
                name=truncate_text(clean_text(item.name), 240) or "unknown",
                result=clean_text(item.result),
                state=clean_text(item.state),
                duration_seconds=item.duration_seconds,
                source_ref=_friendly_source_ref("job", item, source_ref_map),
            )
            for item in selected
        ],
        truncated,
    )


def _select_ranked_tasks(
    tasks: list[CanonicalTask],
    max_items: int,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> tuple[list[TaskEvidence], bool]:
    ranked = sorted(
        tasks,
        key=lambda item: _rank_named_entity(item.name, item.result),
        reverse=True,
    )
    failed = [
        item
        for item in tasks
        if (item.result or "").lower() and (item.result or "").lower() != "succeeded"
    ]
    ordered = dedupe_preserve_order(
        [*(item.source_ref or "" for item in ranked), *(item.source_ref or "" for item in failed)]
    )
    by_ref = {item.source_ref or f"id:{index}": item for index, item in enumerate(tasks)}
    merged: list[CanonicalTask] = []
    for ref in ordered:
        if ref in by_ref:
            merged.append(by_ref[ref])
    if not merged:
        merged = ranked
    selected, truncated = _slice_with_tracking(merged, max_items)
    return (
        [
            TaskEvidence(
                name=truncate_text(clean_text(item.name), 240) or "unknown",
                type=clean_text(item.type),
                result=clean_text(item.result),
                state=clean_text(item.state),
                duration_seconds=item.duration_seconds,
                log_url=clean_text(item.log_url),
                source_ref=_friendly_source_ref("task", item, source_ref_map),
            )
            for item in selected
        ],
        truncated,
    )


def _select_artifacts(
    artifacts: list[CanonicalArtifact],
    max_items: int,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> tuple[list[ArtifactEvidence], bool]:
    selected, truncated = _slice_with_tracking(artifacts, max_items)
    return (
        [
            ArtifactEvidence(
                name=truncate_text(clean_text(item.name), 240) or "unknown",
                type=clean_text(item.type),
                resource_type=clean_text(item.resource_type),
                download_url=clean_text(item.download_url),
                source_ref=_friendly_source_ref("artifact", item, source_ref_map),
            )
            for item in selected
        ],
        truncated,
    )


def build_bucket_2_execution_validation(
    canonical: CanonicalDodDocument,
    max_items_per_section: int = DEFAULT_MAX_ITEMS_PER_SECTION,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> ExecutionValidationEvidence:
    """Build evidence bucket for execution/validation fields."""

    stage_evidence, stage_truncated = _select_ranked_stages(
        canonical.execution_context.stages,
        max_items_per_section,
        source_ref_map,
    )
    job_evidence, job_truncated = _select_ranked_jobs(
        canonical.execution_context.jobs,
        max_items_per_section,
        source_ref_map,
    )
    task_evidence, task_truncated = _select_ranked_tasks(
        canonical.execution_context.tasks,
        max_items_per_section,
        source_ref_map,
    )
    artifact_evidence, artifact_truncated = _select_artifacts(
        canonical.execution_context.artifacts,
        max_items_per_section,
        source_ref_map,
    )

    failed_sample = dedupe_preserve_order(
        [
            truncate_text(clean_text(item.test_name), MAX_SIGNAL_CHARS) or ""
            for item in canonical.quality_context.failed_tests
            if is_meaningful_text(clean_text(item.test_name))
        ]
    )[:max_items_per_section]
    warning_sample = dedupe_preserve_order(
        [
            truncate_text(clean_text(item.test_name), MAX_SIGNAL_CHARS) or ""
            for item in canonical.quality_context.warning_tests
            if is_meaningful_text(clean_text(item.test_name))
        ]
    )[:max_items_per_section]
    failed_sample = [item for item in failed_sample if item]
    warning_sample = [item for item in warning_sample if item]
    missing_test_context = list(canonical.quality_context.missing_quality_context)
    if canonical.quality_context.test_summary.total_tests == 0:
        missing_test_context.append("no test results found")

    test_evidence = TestEvidenceSummary(
        total_runs=canonical.quality_context.test_summary.total_runs,
        total_tests=canonical.quality_context.test_summary.total_tests,
        passed_tests=canonical.quality_context.test_summary.passed_tests,
        failed_tests=canonical.quality_context.test_summary.failed_tests,
        skipped_tests=canonical.quality_context.test_summary.skipped_tests,
        pass_rate=canonical.quality_context.test_summary.pass_rate,
        failed_tests_sample=failed_sample,
        warning_tests_sample=warning_sample,
        missing_test_context=dedupe_preserve_order(missing_test_context),
    )

    implementation_signals = dedupe_preserve_order(
        [
            truncate_text(clean_text(item), MAX_SIGNAL_CHARS) or ""
            for item in canonical.execution_context.implementation_signals
            if is_meaningful_text(clean_text(item))
        ]
    )
    validation_signals = dedupe_preserve_order(
        [
            truncate_text(clean_text(item), MAX_SIGNAL_CHARS) or ""
            for item in canonical.execution_context.validation_signals
            if is_meaningful_text(clean_text(item))
        ]
    )
    deployment_signals = dedupe_preserve_order(
        [
            truncate_text(clean_text(item), MAX_SIGNAL_CHARS) or ""
            for item in canonical.execution_context.deployment_signals
            if is_meaningful_text(clean_text(item))
        ]
    )
    quality_signals = dedupe_preserve_order(
        [
            truncate_text(clean_text(item), MAX_SIGNAL_CHARS) or ""
            for item in canonical.quality_context.quality_signals
            if is_meaningful_text(clean_text(item))
        ]
    )
    implementation_signals = [item for item in implementation_signals if item]
    validation_signals = [item for item in validation_signals if item]
    deployment_signals = [item for item in deployment_signals if item]
    quality_signals = [item for item in quality_signals if item]

    gaps = list(canonical.execution_context.missing_execution_context)
    gaps.extend(canonical.quality_context.missing_quality_context)
    if not stage_evidence:
        gaps.append("no timeline stages found")
    if not deployment_signals:
        gaps.append("no deployment signals found")
    if not artifact_evidence:
        gaps.append("no artifact evidence found")
    if canonical.quality_context.test_summary.total_tests == 0:
        gaps.append("no test results found")

    if stage_truncated or job_truncated or task_truncated or artifact_truncated:
        gaps.append("section truncation applied")

    references = dedupe_preserve_order(
        [
            *(item.source_ref for item in stage_evidence if item.source_ref),
            *(item.source_ref for item in job_evidence if item.source_ref),
            *(item.source_ref for item in task_evidence if item.source_ref),
            *(item.source_ref for item in artifact_evidence if item.source_ref),
        ]
    )

    return ExecutionValidationEvidence(
        target_fields=["testing_performed", "implementation_plan", "validation_plan"],
        service_context=_service_context(canonical),
        stage_evidence=stage_evidence,
        job_evidence=job_evidence,
        task_evidence=task_evidence,
        artifact_evidence=artifact_evidence,
        test_evidence=test_evidence,
        implementation_signals=implementation_signals,
        validation_signals=validation_signals,
        deployment_signals=deployment_signals,
        quality_signals=quality_signals,
        evidence_gaps=dedupe_preserve_order(gaps),
        evidence_references=references,
    )


def _failure_from_task(
    item: CanonicalTask,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> FailureWarningEvidence:
    return FailureWarningEvidence(
        source_type="timeline_task",
        name=truncate_text(clean_text(item.name), 240),
        result=clean_text(item.result),
        message=None,
        source_ref=_friendly_source_ref("task", item, source_ref_map),
    )


def _failure_from_test(
    source_type: str,
    item: CanonicalTestResult,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> FailureWarningEvidence:
    return FailureWarningEvidence(
        source_type=source_type,
        name=truncate_text(clean_text(item.test_name), 240),
        result=clean_text(item.outcome),
        message=truncate_text(clean_text(item.error_message), 400),
        source_ref=_friendly_source_ref("test_result", item, source_ref_map),
    )


def build_bucket_3_rollback_risk(
    canonical: CanonicalDodDocument,
    max_items_per_section: int = DEFAULT_MAX_ITEMS_PER_SECTION,
    source_ref_map: dict[str, EvidenceSourceRef] | None = None,
) -> RollbackRiskEvidence:
    """Build evidence bucket for rollback/risk fields."""

    artifact_evidence, artifact_truncated = _select_artifacts(
        canonical.execution_context.artifacts,
        max_items_per_section,
        source_ref_map,
    )
    rollback_indicators = dedupe_preserve_order(
        [
            truncate_text(clean_text(value), MAX_SIGNAL_CHARS) or ""
            for value in canonical.risk_context.rollback_indicators
            if is_meaningful_text(clean_text(value))
        ]
    )
    rollback_indicators = [value for value in rollback_indicators if value][:max_items_per_section]

    impacted_components = [
        value
        for value in dedupe_preserve_order(
            [
                truncate_text(clean_text(value), MAX_SIGNAL_CHARS) or ""
                for value in canonical.risk_context.impacted_components
                if is_meaningful_text(clean_text(value))
            ]
        )
        if value
    ][:max_items_per_section]

    task_failures = [
        _failure_from_task(item, source_ref_map)
        for item in canonical.execution_context.tasks
        if (item.result or "").lower() and (item.result or "").lower() != "succeeded"
    ]
    failed_tests = [
        _failure_from_test("failed_test", item, source_ref_map)
        for item in canonical.quality_context.failed_tests
    ]
    warning_tests = [
        _failure_from_test("warning_test", item, source_ref_map)
        for item in canonical.quality_context.warning_tests
    ]
    combined = task_failures + failed_tests + warning_tests
    combined, warning_truncated = _slice_with_tracking(combined, max_items_per_section)

    risk_signals = dedupe_preserve_order(
        [
            truncate_text(clean_text(value), MAX_SIGNAL_CHARS) or ""
            for value in canonical.risk_context.risk_signals
            if is_meaningful_text(clean_text(value))
        ]
    )
    risk_signals = [value for value in risk_signals if value]

    gaps = list(canonical.risk_context.missing_risk_context)
    if not artifact_evidence:
        gaps.append("no artifacts found")
    if not rollback_indicators:
        gaps.append("no rollback indicators found")
    if not impacted_components:
        gaps.append("no impacted components detected")
    if canonical.quality_context.test_summary.total_tests == 0:
        gaps.append("no test context available")
    if artifact_truncated or warning_truncated:
        gaps.append("section truncation applied")

    references = dedupe_preserve_order(
        [
            *(item.source_ref for item in artifact_evidence if item.source_ref),
            *(item.source_ref for item in combined if item.source_ref),
        ]
    )

    risk_flags = RiskFlagsEvidence(
        config_change_detected=canonical.risk_context.config_change_detected,
        database_change_detected=canonical.risk_context.database_change_detected,
        infrastructure_change_detected=canonical.risk_context.infrastructure_change_detected,
        dependency_change_detected=canonical.risk_context.dependency_change_detected,
        feature_flag_change_detected=canonical.risk_context.feature_flag_change_detected,
    )

    return RollbackRiskEvidence(
        target_fields=["backout_plan", "risk_impact_analysis"],
        service_context=_service_context(canonical),
        artifact_evidence=artifact_evidence,
        rollback_indicators=rollback_indicators,
        impacted_components=impacted_components,
        risk_flags=risk_flags,
        risk_signals=risk_signals,
        failed_or_warning_evidence=combined,
        evidence_gaps=dedupe_preserve_order(gaps),
        evidence_references=references,
    )


def build_evidence_bundle(
    canonical: CanonicalDodDocument,
    source_path: str | None = None,
    max_items_per_section: int = DEFAULT_MAX_ITEMS_PER_SECTION,
) -> EvidenceBundle:
    """Build all evidence buckets from canonical normalized input."""

    max_items = max(1, int(max_items_per_section))
    source_ref_map: dict[str, EvidenceSourceRef] = {}
    bucket_1 = build_bucket_1_change_intent(canonical, max_items, source_ref_map)
    bucket_2 = build_bucket_2_execution_validation(canonical, max_items, source_ref_map)
    bucket_3 = build_bucket_3_rollback_risk(canonical, max_items, source_ref_map)

    missing_sections = [
        *bucket_1.evidence_gaps,
        *bucket_2.evidence_gaps,
        *bucket_3.evidence_gaps,
    ]
    warnings: list[str] = []
    if bucket_1.evidence_gaps:
        warnings.append("bucket_1_has_gaps")
    if bucket_2.evidence_gaps:
        warnings.append("bucket_2_has_gaps")
    if bucket_3.evidence_gaps:
        warnings.append("bucket_3_has_gaps")
    truncation_applied = any("truncation" in gap for gap in missing_sections)

    metadata = EvidenceGenerationMetadata(
        canonical_schema_version=canonical.schema_version,
        generated_sections=["bucket_1", "bucket_2", "bucket_3"],
        missing_sections=dedupe_preserve_order(missing_sections),
        warnings=dedupe_preserve_order(warnings),
        truncation_applied=truncation_applied,
        max_items_per_section=max_items,
    )
    return EvidenceBundle(
        schema_version="1.0",
        build_id=canonical.build_id,
        organization=canonical.organization,
        project=canonical.project,
        generated_at=datetime.now(UTC),
        source_canonical_path=source_path,
        bucket_1=bucket_1,
        bucket_2=bucket_2,
        bucket_3=bucket_3,
        generation_metadata=metadata,
        source_ref_map=source_ref_map,
    )


def build_evidence_summary(
    bundle: EvidenceBundle,
    bucket_paths: dict[str, str],
) -> dict[str, Any]:
    """Build safe summary payload for CLI/API responses."""

    return {
        "status": "completed",
        "message": "Evidence bucket generation completed.",
        "build_id": bundle.build_id,
        "pipeline_name": bundle.bucket_1.service_context.pipeline_name,
        "bucket_1_counts": {
            "work_items": len(bundle.bucket_1.work_item_evidence),
            "commits": len(bundle.bucket_1.commit_evidence),
            "pull_requests": len(bundle.bucket_1.pull_request_evidence),
        },
        "bucket_2_counts": {
            "stages": len(bundle.bucket_2.stage_evidence),
            "jobs": len(bundle.bucket_2.job_evidence),
            "tasks": len(bundle.bucket_2.task_evidence),
            "artifacts": len(bundle.bucket_2.artifact_evidence),
            "test_runs": bundle.bucket_2.test_evidence.total_runs,
            "failed_tests": bundle.bucket_2.test_evidence.failed_tests,
        },
        "bucket_3_counts": {
            "artifacts": len(bundle.bucket_3.artifact_evidence),
            "failures_or_warnings": len(bundle.bucket_3.failed_or_warning_evidence),
            "risk_signals": len(bundle.bucket_3.risk_signals),
        },
        "evidence_gap_counts": {
            "bucket_1": len(bundle.bucket_1.evidence_gaps),
            "bucket_2": len(bundle.bucket_2.evidence_gaps),
            "bucket_3": len(bundle.bucket_3.evidence_gaps),
        },
        "truncation_applied": bundle.generation_metadata.truncation_applied,
        "output_paths": bucket_paths,
    }
