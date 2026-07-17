"""Deterministic evidence bucket generation from canonical documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
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
    ApplicationCandidateScoreEvidence,
    ApplicationResolutionEvidence,
    ArtifactEvidence,
    BackoutStepDerivationEvidence,
    BackoutStepIgnoredTaskEvidence,
    BackoutStepSourceTaskEvidence,
    BackoutTimeDerivationEvidence,
    ChangeIntentEvidence,
    CommitEvidence,
    EvidenceBundle,
    EvidenceGenerationMetadata,
    EvidenceServiceContext,
    EvidenceSourceRef,
    ExecutionValidationEvidence,
    FailureWarningEvidence,
    JobEvidence,
    LowerEnvironmentStageCandidateEvidence,
    PullRequestEvidence,
    RejectedStageEvidence,
    ResiliencyEvidence,
    RiskFlagsEvidence,
    RollbackRiskEvidence,
    StageEvidence,
    TaskEvidence,
    TestEvidenceSummary,
    UatDeploymentActivityEvidence,
    UatDeploymentEvidence,
    WorkItemEvidence,
)
from backend.app.services.evidence.bucket_3_selection import (
    ENVIRONMENT_PRIORITY,
    backout_step_for_action,
    classify_deployment_action,
    deployment_action_kind,
    display_application_name,
    environment_priority,
    is_deployment_activity_name,
    is_non_deployment_stage_name,
    normalize_application_candidate,
    normalize_environment_name,
    round_up_backout_minutes,
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
_PLANNED_IMPACT_PATTERNS = (
    re.compile(
        r"\b(?:planned|expected)\s+(?:service\s+)?(?:outage|downtime|impact|degradation|"
        r"disruption)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bwill be unavailable\b", re.IGNORECASE),
    re.compile(
        r"\busers?\s+(?:will|may)\s+experience\b.*\b(?:during deployment|"
        r"during the deployment|maintenance window)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:outage|downtime|unavailable|intermittent access)\b.*"
        r"\b(?:minute|minutes|hour|hours)\b",
        re.IGNORECASE,
    ),
)
_HIGH_RISK_PATTERNS = (
    re.compile(r"\b(?:known\s+)?recurring\s+(?:deployment\s+)?failures?\b", re.IGNORECASE),
    re.compile(r"\brepeated\s+(?:historical\s+)?incidents?\b", re.IGNORECASE),
    re.compile(r"\bunresolved\s+critical\s+(?:defect|issue|bug)s?\b", re.IGNORECASE),
    re.compile(r"\bexplicit(?:ly)?\s+high[- ]risk\b|\bhigh[- ]risk designation\b", re.IGNORECASE),
    re.compile(r"\bknown\s+production\s+instability\b", re.IGNORECASE),
    re.compile(
        r"\b(?:failed\s+deployment\s+validation|deployment\s+validation\s+failed)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:failure|occurrence)\s+(?:rate\s+)?(?:greater than|over|above)\s+30%\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:likelihood|classification)\s*:?\s*probable\b", re.IGNORECASE),
)
_APPLICATION_PHRASE_RE = re.compile(
    r"\b((?:[A-Z][A-Za-z0-9&._-]*)(?:\s+[A-Z][A-Za-z0-9&._-]*){0,3}\s+"
    r"(?:[Aa]pplication|[Ss]ervice))\b",
)
@dataclass(frozen=True)
class _TimelineDescendant:
    source_type: str
    item: CanonicalJob | CanonicalTask
    depth: int
    ancestor_names: tuple[str, ...]


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


def _bucket_3_text_sources(
    canonical: CanonicalDodDocument,
    source_ref_map: dict[str, EvidenceSourceRef] | None,
) -> list[tuple[str, str | None]]:
    sources: list[tuple[str, str | None]] = []
    for work_item in canonical.change_context.work_items:
        source_ref = _friendly_source_ref("work_item", work_item, source_ref_map)
        for value in (
            work_item.title,
            work_item.description,
            work_item.acceptance_criteria,
        ):
            if is_meaningful_text(clean_text(value)):
                sources.append((clean_text(value) or "", source_ref))
    for pull_request in canonical.change_context.pull_requests:
        source_ref = _friendly_source_ref("pull_request", pull_request, source_ref_map)
        for value in (pull_request.title, pull_request.description):
            if is_meaningful_text(clean_text(value)):
                sources.append((clean_text(value) or "", source_ref))
    for source_type, items in (
        ("stage", canonical.execution_context.stages),
        ("job", canonical.execution_context.jobs),
        ("task", canonical.execution_context.tasks),
    ):
        for timeline_item in items:
            if is_meaningful_text(clean_text(timeline_item.name)):
                sources.append(
                    (
                        clean_text(timeline_item.name) or "",
                        _friendly_source_ref(source_type, timeline_item, source_ref_map),
                    )
                )
    sources.extend(
        (clean_text(value) or "", None)
        for value in [
            *canonical.change_context.change_summary_signals,
            *canonical.execution_context.deployment_signals,
            *canonical.risk_context.risk_signals,
        ]
        if is_meaningful_text(clean_text(value))
    )
    return sources


def _normalized_status(value: str | None) -> str:
    return re.sub(r"[^a-z]", "", (value or "").lower())


def _is_completed_deployment_record(item: CanonicalStage | CanonicalJob | CanonicalTask) -> bool:
    result = _normalized_status(item.result)
    state = _normalized_status(item.state)
    if result in {"failed", "canceled", "cancelled", "skipped", "abandoned"}:
        return False
    if state in {"canceled", "cancelled", "skipped", "notstarted", "pending"}:
        return False
    return result in {
        "succeeded",
        "succeededwithissues",
        "partiallysucceeded",
    } or state in {"completed", "inprogress"} or item.finish_time is not None


def _container_activity_items(
    canonical: CanonicalDodDocument,
    container: CanonicalStage | CanonicalJob,
    source_type: str,
) -> list[_TimelineDescendant]:
    """Return every descendant in timeline order, with cycle protection and ancestry."""

    if not container.id:
        return []
    records: list[tuple[int, str, CanonicalJob | CanonicalTask]] = []
    fallback_order = 0
    for item_type, items in (
        ("job", canonical.execution_context.jobs),
        ("task", canonical.execution_context.tasks),
    ):
        for item in items:
            order = item.timeline_order
            records.append(
                (
                    order if order is not None else 1_000_000 + fallback_order,
                    item_type,
                    item,
                )
            )
            fallback_order += 1
    records.sort(key=lambda record: record[0])

    children: dict[str, list[tuple[str, CanonicalJob | CanonicalTask]]] = {}
    record_keys: dict[int, str] = {}
    for index, (_, item_type, item) in enumerate(records):
        key = item.id or f"{item_type}:{index}"
        record_keys[id(item)] = key
        if item.parent_id:
            children.setdefault(item.parent_id, []).append((item_type, item))

    descendants: list[_TimelineDescendant] = []
    visited = {container.id}
    pending: list[
        tuple[str, CanonicalJob | CanonicalTask, int, tuple[str, ...]]
    ] = [
        (item_type, item, 1, (container.name,))
        for item_type, item in children.get(container.id, [])
    ]
    while pending:
        item_type, item, depth, ancestor_names = pending.pop(0)
        key = record_keys.get(id(item), item.id or f"{item_type}:{len(descendants)}")
        if key in visited:
            continue
        visited.add(key)
        descendants.append(
            _TimelineDescendant(
                source_type=item_type,
                item=item,
                depth=depth,
                ancestor_names=ancestor_names,
            )
        )
        if item.id:
            pending.extend(
                (
                    child_type,
                    child,
                    depth + 1,
                    (*ancestor_names, item.name),
                )
                for child_type, child in children.get(item.id, [])
            )
    return descendants


def _descendant_classification(
    descendant: _TimelineDescendant,
) -> tuple[str, list[str], str | None]:
    item = descendant.item
    if isinstance(item, CanonicalTask):
        result = classify_deployment_action(
            name=item.name,
            task_type=item.type,
            task_definition=item.task_definition,
            description=item.description,
            command=item.command,
            inputs=item.input_signals,
            parent_context=descendant.ancestor_names,
            log_summary=item.log_summary,
        )
        return result.classification, list(result.classification_evidence), item.task_definition
    result = classify_deployment_action(
        name=item.name,
        parent_context=descendant.ancestor_names,
    )
    return result.classification, list(result.classification_evidence), None


def _ignored_activity_reason(classification: str) -> str:
    reasons = {
        "metadata_lookup": "Does not modify the target environment.",
        "preparation": "Prepares the deployment but does not change the target environment.",
        "approval": "Approval activity does not modify the target environment.",
        "wait": "Wait activity does not modify the target environment.",
        "diagnostic": "Diagnostic activity does not modify the target environment.",
        "test": "Test activity does not modify the target environment.",
        "unknown": "No evidence-supported deployment action was identified.",
    }
    return reasons.get(classification, "Activity does not generate a rollback action.")


def _backout_step_derivation(
    container: CanonicalStage | CanonicalJob,
    descendants: list[_TimelineDescendant],
    source_ref_map: dict[str, EvidenceSourceRef] | None,
) -> BackoutStepDerivationEvidence:
    source_tasks: list[BackoutStepSourceTaskEvidence] = []
    ignored_tasks: list[BackoutStepIgnoredTaskEvidence] = []
    normalized_actions: list[str] = []
    deployment_action_found = False
    for descendant in descendants:
        item = descendant.item
        classification, classification_evidence, task_type = _descendant_classification(
            descendant
        )
        generated_step = backout_step_for_action(classification)
        if generated_step and _is_completed_deployment_record(item):
            source_tasks.append(
                BackoutStepSourceTaskEvidence(
                    record_id=item.id,
                    raw_name=truncate_text(clean_text(item.name), 240) or "unknown",
                    record_type=descendant.source_type,
                    task_type=truncate_text(clean_text(task_type), 240),
                    depth=descendant.depth,
                    ancestor_names=list(descendant.ancestor_names),
                    detected_action=classification,
                    classification_evidence=classification_evidence,
                    generated_step=generated_step,
                    source_ref=_friendly_source_ref(
                        descendant.source_type,
                        item,
                        source_ref_map,
                    ),
                )
            )
            if classification not in normalized_actions:
                normalized_actions.append(classification)
            deployment_action_found = deployment_action_found or classification != (
                "deployment_validation"
            )
            continue
        reason = (
            "Activity did not complete successfully."
            if generated_step
            else _ignored_activity_reason(classification)
        )
        ignored_tasks.append(
            BackoutStepIgnoredTaskEvidence(
                record_id=item.id,
                raw_name=truncate_text(clean_text(item.name), 240) or "unknown",
                record_type=descendant.source_type,
                task_type=truncate_text(clean_text(task_type), 240),
                depth=descendant.depth,
                ancestor_names=list(descendant.ancestor_names),
                classification=classification,
                reason=reason,
                source_ref=_friendly_source_ref(descendant.source_type, item, source_ref_map),
            )
        )
    fallback_used = not deployment_action_found
    return BackoutStepDerivationEvidence(
        recursive_traversal_used=True,
        traversal_complete=True,
        selected_stage_id=container.id,
        descendant_count=len(descendants),
        max_depth=max((item.depth for item in descendants), default=0),
        source_tasks=source_tasks,
        ignored_tasks=ignored_tasks,
        normalized_actions=normalized_actions,
        fallback_used=fallback_used,
        fallback_reason=(
            "No evidence-supported deployment action was identified beneath the selected "
            "lower-environment stage."
            if fallback_used
            else None
        ),
    )


def _is_mutating_descendant(descendant: _TimelineDescendant) -> bool:
    classification, _, _ = _descendant_classification(descendant)
    return (
        classification != "deployment_validation"
        and backout_step_for_action(classification) is not None
        and _is_completed_deployment_record(descendant.item)
    )


def _stage_rejection_reason(
    container: CanonicalStage | CanonicalJob,
    environment: str | None,
) -> str | None:
    if environment == "PRODUCTION":
        return "Production stages cannot be used for backout-duration estimation."
    if environment is None:
        return "Not a lower-environment deployment stage."
    if is_non_deployment_stage_name(container.name):
        return "Stage is build, scan, artifact, approval-only, or test-only activity."
    if not _is_completed_deployment_record(container):
        return "Stage was skipped, canceled, failed, or did not substantially complete."
    if container.start_time is None or container.finish_time is None:
        return "Deployment-stage start or finish timing is missing."
    duration = (container.finish_time - container.start_time).total_seconds()
    if duration <= 0:
        return "Deployment-stage timing is not a positive duration."
    return None


def _lower_environment_deployment_evidence(
    canonical: CanonicalDodDocument,
    max_items: int,
    source_ref_map: dict[str, EvidenceSourceRef] | None,
) -> tuple[
    UatDeploymentEvidence,
    list[LowerEnvironmentStageCandidateEvidence],
    list[RejectedStageEvidence],
    BackoutTimeDerivationEvidence,
    BackoutStepDerivationEvidence,
    list[str],
]:
    stage_ids = {stage.id for stage in canonical.execution_context.stages if stage.id}
    containers: list[tuple[str, CanonicalStage | CanonicalJob]] = [
        ("stage", stage) for stage in canonical.execution_context.stages
    ]
    containers.extend(
        ("job", job)
        for job in canonical.execution_context.jobs
        if normalize_environment_name(job.name) is not None
        and (not job.parent_id or job.parent_id not in stage_ids)
    )

    candidates: list[LowerEnvironmentStageCandidateEvidence] = []
    rejected: list[RejectedStageEvidence] = []
    valid: list[
        tuple[
            int,
            int,
            str,
            CanonicalStage | CanonicalJob,
            list[_TimelineDescendant],
            LowerEnvironmentStageCandidateEvidence,
        ]
    ] = []
    timing_missing = False
    for index, (source_type, container) in enumerate(containers):
        environment = normalize_environment_name(container.name)
        descendants = _container_activity_items(canonical, container, source_type)
        activity_items = [
            descendant
            for descendant in descendants
            if _is_mutating_descendant(descendant)
        ]
        duration = (
            (container.finish_time - container.start_time).total_seconds()
            if container.start_time is not None and container.finish_time is not None
            else None
        )
        source_ref = _friendly_source_ref(source_type, container, source_ref_map)
        candidate = LowerEnvironmentStageCandidateEvidence(
            stage_name=clean_text(container.name) or "unknown",
            normalized_environment=environment,
            state=clean_text(container.state),
            result=clean_text(container.result),
            start_time=container.start_time,
            finish_time=container.finish_time,
            duration_seconds=duration,
            deployment_activities=[item.item.name for item in activity_items],
            source_ref=source_ref,
        )
        if environment is not None:
            candidates.append(candidate)
        reason = _stage_rejection_reason(container, environment)
        if reason is not None:
            rejected.append(RejectedStageEvidence(stage_name=container.name, reason=reason))
            if "timing" in reason.lower() and environment not in {None, "PRODUCTION"}:
                timing_missing = True
            continue
        valid.append(
            (
                environment_priority(environment),
                index,
                source_type,
                container,
                descendants,
                candidate,
            )
        )

    valid.sort(key=lambda item: (item[0], item[1]))
    selected = valid[0] if valid else None
    if selected is not None:
        _, _, source_type, container, descendants, selected_candidate = selected
        selected_candidate.selected = True
        selected_environment = normalize_environment_name(container.name)
        selected_ref = _friendly_source_ref(source_type, container, source_ref_map)
        step_derivation = _backout_step_derivation(
            container,
            descendants,
            source_ref_map,
        )
        activity_items = [
            descendant
            for descendant in descendants
            if _is_mutating_descendant(descendant)
        ][:max_items]
        activity_evidence = [
            UatDeploymentActivityEvidence(
                name=truncate_text(clean_text(descendant.item.name), 240) or "unknown",
                status=(
                    clean_text(descendant.item.result) or clean_text(descendant.item.state)
                ),
                duration_seconds=descendant.item.duration_seconds,
                source_ref=_friendly_source_ref(
                    descendant.source_type,
                    descendant.item,
                    source_ref_map,
                ),
            )
            for descendant in activity_items
        ]
        assert container.start_time is not None
        assert container.finish_time is not None
        duration = (container.finish_time - container.start_time).total_seconds()
        deployment = UatDeploymentEvidence(
            stage_name=clean_text(container.name),
            selected_environment=selected_environment,
            stage_start_time=container.start_time,
            stage_finish_time=container.finish_time,
            activities=activity_evidence,
            total_deployment_duration_seconds=duration,
        )
        derivation = BackoutTimeDerivationEvidence(
            environment_priority=list(ENVIRONMENT_PRIORITY),
            selected_environment=selected_environment,
            selected_stage_name=clean_text(container.name),
            stage_start_time=container.start_time,
            stage_finish_time=container.finish_time,
            source_duration_seconds=duration,
            final_estimate_minutes=round_up_backout_minutes(duration),
            evidence_refs=dedupe_preserve_order(
                [
                    selected_ref,
                    *(item.source_ref for item in activity_evidence if item.source_ref),
                ]
            ),
        )
        for _, _, _, other, _, _ in valid[1:]:
            other_environment = normalize_environment_name(other.name)
            if other_environment == selected_environment:
                reason = "Another valid stage for the selected environment was preferred."
            else:
                reason = f"Lower priority than selected {selected_environment} environment."
            rejected.append(RejectedStageEvidence(stage_name=other.name, reason=reason))
        return deployment, candidates, rejected, derivation, step_derivation, []

    warnings = ["BACKOUT_DURATION_LOWER_ENVIRONMENT_NOT_FOUND"]
    if timing_missing:
        warnings.append("BACKOUT_DURATION_STAGE_TIMING_MISSING")
    return (
        UatDeploymentEvidence(),
        candidates,
        rejected,
        BackoutTimeDerivationEvidence(environment_priority=list(ENVIRONMENT_PRIORITY)),
        BackoutStepDerivationEvidence(),
        warnings,
    )


def _build_resiliency_evidence(
    sources: list[tuple[str, str | None]],
) -> ResiliencyEvidence:
    active_active = False
    alternate_region: str | None = None
    rolling_deployment = False
    traffic_shift = False
    passive_instance_available = False
    evidence_refs: list[str] = []
    for text, source_ref in sources:
        lowered = text.lower()
        matched = False
        if re.search(r"\bactive[- ]active\b", lowered):
            active_active = True
            matched = True
        if re.search(
            r"\b(?:alternate|secondary|separate|passive)\s+(?:region|data center)\b",
            lowered,
        ):
            alternate_region = alternate_region or truncate_text(text, MAX_SIGNAL_CHARS)
            matched = True
        if "rolling deployment" in lowered or "rolling update" in lowered:
            rolling_deployment = True
            matched = True
        if re.search(
            r"\btraffic\b.*\b(?:remain|remains|shift|shifted|route|routed|healthy instance)\b",
            lowered,
        ):
            traffic_shift = True
            matched = True
        if re.search(
            r"\b(?:passive|secondary)\s+(?:instance|region|data center)\b.*"
            r"\b(?:available|healthy|active|remains)\b",
            lowered,
        ) or re.search(r"\bdeployment affects only the passive\b", lowered):
            passive_instance_available = True
            matched = True
        if matched and source_ref:
            evidence_refs.append(source_ref)
    return ResiliencyEvidence(
        active_active=active_active,
        alternate_region=alternate_region,
        rolling_deployment=rolling_deployment,
        traffic_shift=traffic_shift,
        passive_instance_available=passive_instance_available,
        evidence_refs=dedupe_preserve_order(evidence_refs),
    )


def _collect_matching_evidence(
    sources: list[tuple[str, str | None]],
    patterns: tuple[re.Pattern[str], ...],
    max_items: int,
) -> tuple[list[str], list[str]]:
    values: list[str] = []
    references: list[str] = []
    for text, source_ref in sources:
        if not any(pattern.search(text) for pattern in patterns):
            continue
        value = truncate_text(text, MAX_SIGNAL_CHARS)
        if value:
            values.append(value)
        if source_ref:
            references.append(source_ref)
    return (
        dedupe_preserve_order(values)[:max_items],
        dedupe_preserve_order(references),
    )


def _deployment_target(name: str | None) -> str | None:
    text = clean_text(name) or ""
    patterns = (
        r"\b(?:apply\s+solution\s+upgrade|upgrade\s+solution|import\s+solution|"
        r"deploy\s+solution)\s+(.+)$",
        r"\b(?:deploy\s+(?:application|app|service)|install\s+package|deploy\s+package)"
        r"\s+(.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            target = re.split(
                r"\s+to\s+(?:uat|qa|test|intg|integration|sit|dev|development|prod|production)\b",
                match.group(1),
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            return target.strip(" ._-:") or None
    return None


def _application_resolution(
    canonical: CanonicalDodDocument,
    deployment: UatDeploymentEvidence,
    max_items: int,
) -> ApplicationResolutionEvidence:
    ranked: dict[str, dict[str, Any]] = {}

    def add_candidate(value: str | None, source: str, base_score: int) -> None:
        cleaned = truncate_text(clean_text(value), 160)
        normalized = normalize_application_candidate(cleaned)
        if not cleaned or not normalized or "refs/heads/" in cleaned.lower():
            return
        entry = ranked.setdefault(
            normalized,
            {"candidate": cleaned, "base_score": base_score, "sources": []},
        )
        entry["base_score"] = max(int(entry["base_score"]), base_score)
        if source not in entry["sources"]:
            entry["sources"].append(source)

    stage_ids = {
        stage.id
        for stage in canonical.execution_context.stages
        if stage.id and normalize_environment_name(stage.name) == "PRODUCTION"
    }
    production_job_ids = {
        job.id
        for job in canonical.execution_context.jobs
        if job.id
        and (
            (job.parent_id and job.parent_id in stage_ids)
            or normalize_environment_name(job.name) == "PRODUCTION"
        )
    }
    production_parent_ids = stage_ids | production_job_ids
    production_targets: list[str] = []
    for task in canonical.execution_context.tasks:
        if (
            task.parent_id
            and task.parent_id in production_parent_ids
            and is_deployment_activity_name(task.name)
        ):
            target = _deployment_target(task.name)
            if target:
                production_targets.append(target)
                add_candidate(target, "production_deployment", 120)

    repository = canonical.run_context.repository_name
    pipeline = canonical.run_context.pipeline_name
    add_candidate(repository, "repository", 100)
    add_candidate(pipeline, "pipeline", 90)

    lower_targets: list[str] = []
    lower_environment_source = (
        f"{deployment.selected_environment.lower()}_deployment"
        if deployment.selected_environment
        else "lower_environment_deployment"
    )
    for activity in deployment.activities:
        target = _deployment_target(activity.name)
        if target:
            lower_targets.append(target)
            add_candidate(target, lower_environment_source, 80)

    for task in canonical.execution_context.tasks:
        if not is_deployment_activity_name(task.name):
            continue
        target = _deployment_target(task.name)
        kind = deployment_action_kind(task.name)
        if target and kind in {
            "solution_upgrade",
            "solution_deployment",
            "solution_import",
            "solution_deploy",
            "package_deployment",
            "package_deploy",
        }:
            add_candidate(target, "solution_or_package", 75)

    for work_item in canonical.change_context.work_items:
        for match in _APPLICATION_PHRASE_RE.finditer(clean_text(work_item.title) or ""):
            add_candidate(match.group(1), "work_item_title", 50)
        for value in (work_item.description, work_item.acceptance_criteria):
            for match in _APPLICATION_PHRASE_RE.finditer(clean_text(value) or ""):
                add_candidate(match.group(1), "change_description", 35)

    for component in canonical.risk_context.impacted_components:
        add_candidate(component, "impacted_component", 60)
    add_candidate(canonical.project, "project", 10)

    repository_key = normalize_application_candidate(repository)
    if repository_key and repository_key in ranked:
        repository_tokens = {
            token for token in repository_key.split() if len(token) >= 3 and token != "application"
        }

        def aligns_with_repository(target: str) -> bool:
            target_tokens = {
                token
                for token in normalize_application_candidate(target).split()
                if len(token) >= 3
            }
            return bool(repository_tokens & target_tokens)

        if any(aligns_with_repository(target) for target in lower_targets):
            sources = ranked[repository_key]["sources"]
            if lower_environment_source not in sources:
                sources.append(lower_environment_source)
        for target in production_targets:
            target_key = normalize_application_candidate(target)
            if target_key == repository_key or not aligns_with_repository(target):
                continue
            repository_entry = ranked[repository_key]
            repository_entry["base_score"] = 120
            if "production_deployment" not in repository_entry["sources"]:
                repository_entry["sources"].append("production_deployment")
            technical_target = ranked.get(target_key)
            if technical_target is not None:
                technical_target["base_score"] = min(
                    int(technical_target["base_score"]),
                    80,
                )

    candidate_scores: list[ApplicationCandidateScoreEvidence] = []
    for _normalized, entry in ranked.items():
        independent_bonus = min(max(len(entry["sources"]) - 1, 0) * 5, 15)
        score = min(int(entry["base_score"]) + independent_bonus, 120)
        candidate_scores.append(
            ApplicationCandidateScoreEvidence(
                candidate=str(entry["candidate"]),
                score=score,
                sources=list(entry["sources"]),
            )
        )
    candidate_scores.sort(
        key=lambda item: (-item.score, normalize_application_candidate(item.candidate))
    )
    candidate_scores = candidate_scores[:max_items]
    if not candidate_scores:
        candidate_scores = [
            ApplicationCandidateScoreEvidence(
                candidate="deployed application",
                score=0,
                sources=["deterministic_fallback"],
            )
        ]
    selected = candidate_scores[0]
    selected_sources = set(selected.sources)
    if "repository" in selected_sources:
        has_lower_deployment = any(
            source.endswith("_deployment") and source != "production_deployment"
            for source in selected_sources
        )
        if (
            "production_deployment" in selected_sources
            and "pipeline" in selected_sources
            and has_lower_deployment
        ):
            reason = (
                "Mapped production solution evidence to matching repository/pipeline identity "
                "and lower-environment solution deployment evidence."
            )
        elif "pipeline" in selected_sources and has_lower_deployment:
            reason = (
                "Matched repository/pipeline identity and lower-environment solution "
                "deployment evidence."
            )
        elif has_lower_deployment:
            reason = "Matched repository identity and lower-environment deployment evidence."
        else:
            reason = "Matched repository identity as the strongest deployed-application evidence."
    elif "production_deployment" in selected_sources:
        reason = "Matched explicit production deployment application or solution evidence."
    elif "pipeline" in selected_sources:
        reason = "Selected the normalized pipeline application identity."
    else:
        reason = "Selected the highest-ranked concrete application candidate."
    return ApplicationResolutionEvidence(
        selected_application=selected.candidate,
        display_name=display_application_name(selected.candidate),
        selection_reason=reason,
        candidate_scores=candidate_scores,
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

    sources = _bucket_3_text_sources(canonical, source_ref_map)
    (
        uat_deployment,
        environment_candidates,
        rejected_stages,
        backout_time_derivation,
        backout_step_derivation,
        bucket_3_warnings,
    ) = _lower_environment_deployment_evidence(
        canonical,
        max_items_per_section,
        source_ref_map,
    )
    resiliency_evidence = _build_resiliency_evidence(sources)
    planned_impact_evidence, planned_impact_refs = _collect_matching_evidence(
        sources,
        _PLANNED_IMPACT_PATTERNS,
        max_items_per_section,
    )
    high_risk_evidence, high_risk_refs = _collect_matching_evidence(
        sources,
        _HIGH_RISK_PATTERNS,
        max_items_per_section,
    )
    application_resolution = _application_resolution(
        canonical,
        uat_deployment,
        max_items_per_section,
    )
    application_candidates = [
        item.candidate for item in application_resolution.candidate_scores
    ]

    gaps = list(canonical.risk_context.missing_risk_context)
    if not artifact_evidence:
        gaps.append("no artifacts found")
    if not rollback_indicators:
        gaps.append("no rollback indicators found")
    if not impacted_components:
        gaps.append("no impacted components detected")
    if canonical.quality_context.test_summary.total_tests == 0:
        gaps.append("no test context available")
    if "BACKOUT_DURATION_LOWER_ENVIRONMENT_NOT_FOUND" in bucket_3_warnings:
        gaps.append("no valid lower-environment deployment stage found")
    if artifact_truncated or warning_truncated:
        gaps.append("section truncation applied")

    references = dedupe_preserve_order(
        [
            *(item.source_ref for item in artifact_evidence if item.source_ref),
            *(item.source_ref for item in combined if item.source_ref),
            *(item.source_ref for item in uat_deployment.activities if item.source_ref),
            *(
                item.source_ref
                for item in backout_step_derivation.source_tasks
                if item.source_ref
            ),
            *backout_time_derivation.evidence_refs,
            *resiliency_evidence.evidence_refs,
            *planned_impact_refs,
            *high_risk_refs,
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
        uat_deployment=uat_deployment,
        environment_candidates=environment_candidates,
        rejected_stages=rejected_stages,
        backout_time_derivation=backout_time_derivation,
        backout_step_derivation=backout_step_derivation,
        resiliency_evidence=resiliency_evidence,
        application_candidates=application_candidates,
        application_resolution=application_resolution,
        planned_impact_evidence=planned_impact_evidence,
        high_risk_evidence=high_risk_evidence,
        failed_or_warning_evidence=combined,
        warnings=bucket_3_warnings,
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
    warnings.extend(bucket_3.warnings)
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
