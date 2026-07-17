"""Deterministic canonical normalization from raw collection bundles."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from backend.app.models.canonical import (
    CanonicalArtifact,
    CanonicalCommit,
    CanonicalDodDocument,
    CanonicalJob,
    CanonicalPullRequest,
    CanonicalScanSummary,
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

_DEPLOYMENT_TERMS = [
    "deploy",
    "deployment",
    "release",
    "environment",
    "prod",
    "lower",
    "dev",
    "test",
    "stage",
]
_IMPLEMENTATION_TERMS = [
    "build",
    "compile",
    "package",
    "publish",
    "artifact",
    "archive",
    "docker",
]
_VALIDATION_TERMS = [
    "test",
    "validate",
    "scan",
    "check",
    "lint",
    "quality",
    "verify",
]
_SKIPPED_TEST_OUTCOMES = {"skipped", "notexecuted", "notapplicable", "not applicable"}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.isdigit():
            return int(cleaned)
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any) -> datetime | None:
    text = _as_str(value)
    if not text:
        return None
    if text.startswith("0001-01-01"):
        return None
    try:
        if text.endswith("Z"):
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _duration_seconds(start_time: datetime | None, finish_time: datetime | None) -> float | None:
    if start_time is None or finish_time is None:
        return None
    seconds = (finish_time - start_time).total_seconds()
    return seconds if seconds >= 0 else None


def _identity_to_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, dict):
        for key in ("displayName", "uniqueName", "mailAddress", "name", "id"):
            candidate = _as_str(value.get(key))
            if candidate:
                return candidate
    return None


def _unique_non_empty(values: Sequence[str | None]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _normalize_run_context(build_payload: dict[str, Any], build_id: int) -> RunContext:
    definition = _as_dict(build_payload.get("definition"))
    repository = _as_dict(build_payload.get("repository"))
    web_links = _as_dict(_as_dict(build_payload.get("_links")).get("web"))
    return RunContext(
        build_id=build_id,
        build_number=_as_str(build_payload.get("buildNumber")),
        pipeline_id=_as_int(definition.get("id")),
        pipeline_name=_as_str(definition.get("name")),
        repository_id=_as_str(repository.get("id")),
        repository_name=_as_str(repository.get("name")),
        repository_type=_as_str(repository.get("type")),
        source_branch=_as_str(build_payload.get("sourceBranch")),
        source_version=_as_str(build_payload.get("sourceVersion")),
        requested_by=_identity_to_string(build_payload.get("requestedBy")),
        requested_for=_identity_to_string(build_payload.get("requestedFor")),
        queue_time=_parse_datetime(build_payload.get("queueTime")),
        start_time=_parse_datetime(build_payload.get("startTime")),
        finish_time=_parse_datetime(build_payload.get("finishTime")),
        status=_as_str(build_payload.get("status")),
        result=_as_str(build_payload.get("result")),
        reason=_as_str(build_payload.get("reason")),
        url=_as_str(build_payload.get("url")),
        web_url=_as_str(web_links.get("href")),
    )


def _normalize_work_items(raw_work_items: Any) -> list[CanonicalWorkItem]:
    value = _as_list(_as_dict(raw_work_items).get("value"))
    normalized: list[CanonicalWorkItem] = []
    for index, item in enumerate(value):
        payload = _as_dict(item)
        fields = _as_dict(payload.get("fields"))
        source_id = _as_int(fields.get("System.Id")) or _as_int(payload.get("id"))
        if source_id is None:
            continue
        tags_raw = _as_str(fields.get("System.Tags")) or ""
        tags = [tag.strip() for tag in tags_raw.split(";") if tag.strip()]
        normalized.append(
            CanonicalWorkItem(
                id=source_id,
                type=_as_str(fields.get("System.WorkItemType")),
                title=_as_str(fields.get("System.Title")),
                state=_as_str(fields.get("System.State")),
                reason=_as_str(fields.get("System.Reason")),
                assigned_to=_identity_to_string(fields.get("System.AssignedTo")),
                created_by=_identity_to_string(fields.get("System.CreatedBy")),
                changed_by=_identity_to_string(fields.get("System.ChangedBy")),
                area_path=_as_str(fields.get("System.AreaPath")),
                iteration_path=_as_str(fields.get("System.IterationPath")),
                tags=tags,
                description=_as_str(fields.get("System.Description")),
                acceptance_criteria=_as_str(
                    fields.get("Microsoft.VSTS.Common.AcceptanceCriteria")
                ),
                priority=_as_int(fields.get("Microsoft.VSTS.Common.Priority")),
                business_value=_as_int(fields.get("Microsoft.VSTS.Common.BusinessValue")),
                url=_as_str(payload.get("url")),
                source_ref=f"raw.work_items.value[{index}]",
            )
        )
    return normalized


def _normalize_commits(raw_changes: Any) -> list[CanonicalCommit]:
    value = _as_list(_as_dict(raw_changes).get("value"))
    commits: list[CanonicalCommit] = []
    for index, item in enumerate(value):
        payload = _as_dict(item)
        commit_id = _as_str(payload.get("id"))
        if not commit_id:
            continue
        author = _as_dict(payload.get("author"))
        committer = _as_dict(payload.get("committer"))
        authored_at = _parse_datetime(payload.get("timestamp")) or _parse_datetime(
            payload.get("date")
        )
        committed_at = _parse_datetime(committer.get("date")) or authored_at
        commits.append(
            CanonicalCommit(
                id=commit_id,
                message=_as_str(payload.get("message")) or _as_str(payload.get("comment")),
                author_name=_identity_to_string(author),
                author_email=_as_str(author.get("uniqueName"))
                or _as_str(author.get("email"))
                or _as_str(author.get("id")),
                authored_at=authored_at,
                committer_name=_identity_to_string(committer) or _identity_to_string(author),
                committed_at=committed_at,
                url=_as_str(payload.get("location")) or _as_str(payload.get("url")),
                source_ref=f"raw.changes.value[{index}]",
            )
        )
    return commits


def _extract_pr_candidates(raw_pull_requests: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    candidates: list[tuple[dict[str, Any], str]] = []
    for index, item in enumerate(_as_list(raw_pull_requests.get("pull_requests"))):
        payload = _as_dict(item)
        if payload:
            candidates.append((payload, f"raw.pull_requests.pull_requests[{index}]"))

    value_payload = _as_list(raw_pull_requests.get("value"))
    for index, item in enumerate(value_payload):
        payload = _as_dict(item)
        if payload:
            candidates.append((payload, f"raw.pull_requests.value[{index}]"))

    query_payload = _as_dict(raw_pull_requests.get("query"))
    results = _as_list(query_payload.get("results"))
    for result_index, result in enumerate(results):
        result_dict = _as_dict(result)
        if not result_dict:
            continue
        result_items = _as_list(
            result_dict.get("pullRequests")
            or result_dict.get("value")
            or result_dict.get("matches")
            or result_dict.get("items")
        )
        for item_index, item in enumerate(result_items):
            payload = _as_dict(item)
            if payload:
                source_ref = (
                    f"raw.pull_requests.query.results[{result_index}].items[{item_index}]"
                )
                candidates.append((payload, source_ref))
    return candidates


def _extract_commit_ids_for_pr(
    pull_request_payload: dict[str, Any],
    pr_id: int,
    raw_pull_requests: dict[str, Any],
) -> list[str]:
    commit_ids: list[str] = []
    for path in ("lastMergeSourceCommit.commitId", "lastMergeCommit.commitId"):
        current: Any = pull_request_payload
        for key in path.split("."):
            current = _as_dict(current).get(key)
        commit_value = _as_str(current)
        if commit_value:
            commit_ids.append(commit_value)

    commits_lookup = _as_dict(raw_pull_requests.get("commits"))
    commit_payload = _as_dict(commits_lookup.get(str(pr_id)))
    commit_values = _as_list(commit_payload.get("value"))
    for item in commit_values:
        commit_id = _as_str(_as_dict(item).get("commitId")) or _as_str(_as_dict(item).get("id"))
        if commit_id:
            commit_ids.append(commit_id)
    return _unique_non_empty(commit_ids)


def _normalize_pull_requests(raw_pull_requests: Any) -> list[CanonicalPullRequest]:
    payload = _as_dict(raw_pull_requests)
    candidates = _extract_pr_candidates(payload)
    normalized: list[CanonicalPullRequest] = []
    seen_ids: set[int] = set()
    for candidate, source_ref in candidates:
        pr_id = _as_int(candidate.get("pullRequestId")) or _as_int(candidate.get("id"))
        if pr_id is None or pr_id in seen_ids:
            continue
        seen_ids.add(pr_id)
        reviewers = [
            name
            for reviewer in _as_list(candidate.get("reviewers"))
            for name in [_identity_to_string(reviewer)]
            if name
        ]
        normalized.append(
            CanonicalPullRequest(
                id=pr_id,
                title=_as_str(candidate.get("title")),
                description=_as_str(candidate.get("description")),
                status=_as_str(candidate.get("status")),
                created_by=_identity_to_string(candidate.get("createdBy")),
                source_branch=_as_str(candidate.get("sourceRefName")),
                target_branch=_as_str(candidate.get("targetRefName")),
                merge_status=_as_str(candidate.get("mergeStatus")),
                is_draft=candidate.get("isDraft")
                if isinstance(candidate.get("isDraft"), bool)
                else None,
                reviewers=_unique_non_empty(reviewers),
                commit_ids=_extract_commit_ids_for_pr(candidate, pr_id, payload),
                url=_as_str(candidate.get("url")),
                source_ref=source_ref,
            )
        )
    return normalized


def _normalize_change_context(raw: dict[str, Any]) -> ChangeContext:
    work_items = _normalize_work_items(raw.get("work_items"))
    commits = _normalize_commits(raw.get("changes"))
    pull_requests = _normalize_pull_requests(raw.get("pull_requests"))

    signals = _unique_non_empty(
        [work_item.title for work_item in work_items]
        + [pull_request.title for pull_request in pull_requests]
        + [commit.message for commit in commits]
    )
    missing: list[str] = []
    if not work_items:
        missing.append("work_items_missing")
    if not commits:
        missing.append("commits_missing")
    if not pull_requests:
        missing.append("pull_requests_missing_or_not_associated")

    return ChangeContext(
        work_items=work_items,
        commits=commits,
        pull_requests=pull_requests,
        change_summary_signals=signals,
        missing_change_context=missing,
    )


def _record_duration(
    record: dict[str, Any],
) -> tuple[datetime | None, datetime | None, float | None]:
    start_time = _parse_datetime(record.get("startTime"))
    finish_time = _parse_datetime(record.get("finishTime"))
    return start_time, finish_time, _duration_seconds(start_time, finish_time)


def _timeline_input_signals(record: dict[str, Any]) -> dict[str, str]:
    """Keep only classification-relevant timeline inputs; never expose them in field text."""

    inputs = _as_dict(record.get("inputs"))
    allowed = {
        "solution",
        "solutionname",
        "solutionpath",
        "package",
        "packagepath",
        "environment",
        "environmenttarget",
        "targetenvironment",
        "command",
        "script",
        "inlinescript",
        "clicommand",
    }
    return {
        str(key): value.strip()
        for key, raw_value in inputs.items()
        if re.sub(r"[^a-z]", "", str(key).lower()) in allowed
        and isinstance(raw_value, str)
        and (value := raw_value.strip())
    }


def _normalize_timeline_and_signals(
    raw_timeline: Any,
) -> tuple[
    list[CanonicalStage],
    list[CanonicalJob],
    list[CanonicalTask],
    list[str],
    list[str],
    list[str],
]:
    timeline = _as_dict(raw_timeline)
    records = _as_list(timeline.get("records"))
    stages: list[CanonicalStage] = []
    jobs: list[CanonicalJob] = []
    tasks: list[CanonicalTask] = []
    deployment_signals: list[str] = []
    implementation_signals: list[str] = []
    validation_signals: list[str] = []

    for index, item in enumerate(records):
        record = _as_dict(item)
        record_type = (_as_str(record.get("type")) or "").lower()
        name = _as_str(record.get("name")) or "unknown"
        start_time, finish_time, duration = _record_duration(record)
        source_ref = f"raw.timeline.records[{index}]"

        lowered_name = name.lower()
        if _contains_any(lowered_name, _DEPLOYMENT_TERMS):
            deployment_signals.append(name)
        if _contains_any(lowered_name, _IMPLEMENTATION_TERMS):
            implementation_signals.append(name)
        if _contains_any(lowered_name, _VALIDATION_TERMS):
            validation_signals.append(name)

        if "stage" in record_type:
            stages.append(
                CanonicalStage(
                    id=_as_str(record.get("id")),
                    name=name,
                    timeline_order=index,
                    state=_as_str(record.get("state")),
                    result=_as_str(record.get("result")),
                    start_time=start_time,
                    finish_time=finish_time,
                    duration_seconds=duration,
                    source_ref=source_ref,
                )
            )
            continue

        if "job" in record_type or "phase" in record_type:
            jobs.append(
                CanonicalJob(
                    id=_as_str(record.get("id")),
                    name=name,
                    parent_id=_as_str(record.get("parentId")),
                    timeline_order=index,
                    state=_as_str(record.get("state")),
                    result=_as_str(record.get("result")),
                    start_time=start_time,
                    finish_time=finish_time,
                    duration_seconds=duration,
                    source_ref=source_ref,
                )
            )
            continue

        task_metadata = _as_dict(record.get("task"))
        input_signals = _timeline_input_signals(record)
        command = next(
            (
                value
                for key, value in input_signals.items()
                if re.sub(r"[^a-z]", "", key.lower())
                in {"command", "script", "inlinescript", "clicommand"}
            ),
            _as_str(record.get("command")),
        )
        tasks.append(
            CanonicalTask(
                id=_as_str(record.get("id")),
                name=name,
                parent_id=_as_str(record.get("parentId")),
                type=_as_str(record.get("type")),
                task_definition=(
                    _as_str(task_metadata.get("name"))
                    or _as_str(record.get("identifier"))
                    or _as_str(record.get("refName"))
                ),
                description=_as_str(record.get("description")),
                command=command,
                input_signals=input_signals,
                log_summary=(
                    _as_str(record.get("logSummary"))
                    or _as_str(record.get("currentOperation"))
                ),
                timeline_order=index,
                state=_as_str(record.get("state")),
                result=_as_str(record.get("result")),
                start_time=start_time,
                finish_time=finish_time,
                duration_seconds=duration,
                log_url=_as_str(_as_dict(record.get("log")).get("url")),
                source_ref=source_ref,
            )
        )

    return (
        stages,
        jobs,
        tasks,
        _unique_non_empty(deployment_signals),
        _unique_non_empty(implementation_signals),
        _unique_non_empty(validation_signals),
    )


def _normalize_artifacts(raw_artifacts: Any) -> list[CanonicalArtifact]:
    payload = _as_dict(raw_artifacts)
    value = _as_list(payload.get("value"))
    artifacts: list[CanonicalArtifact] = []
    for index, item in enumerate(value):
        artifact = _as_dict(item)
        resource = _as_dict(artifact.get("resource"))
        name = _as_str(artifact.get("name")) or f"artifact-{index}"
        artifacts.append(
            CanonicalArtifact(
                name=name,
                type=_as_str(artifact.get("type")),
                resource_type=_as_str(resource.get("type")),
                download_url=_as_str(resource.get("downloadUrl")),
                source_ref=f"raw.artifacts.value[{index}]",
            )
        )
    return artifacts


def _normalize_execution_context(raw: dict[str, Any]) -> ExecutionContext:
    stages, jobs, tasks, deployment_signals, implementation_signals, validation_signals = (
        _normalize_timeline_and_signals(raw.get("timeline"))
    )
    artifacts = _normalize_artifacts(raw.get("artifacts"))
    implementation_signals = _unique_non_empty(
        implementation_signals + [artifact.name for artifact in artifacts]
    )

    missing: list[str] = []
    if not stages and not jobs and not tasks:
        missing.append("timeline_records_missing")
    if not artifacts:
        missing.append("artifacts_missing")

    return ExecutionContext(
        stages=stages,
        jobs=jobs,
        tasks=tasks,
        artifacts=artifacts,
        deployment_signals=deployment_signals,
        implementation_signals=implementation_signals,
        validation_signals=validation_signals,
        missing_execution_context=missing,
    )


def _extract_test_runs(raw_test_runs: Any) -> list[CanonicalTestRun]:
    value = _as_list(_as_dict(raw_test_runs).get("value"))
    runs: list[CanonicalTestRun] = []
    for index, item in enumerate(value):
        run = _as_dict(item)
        run_id = _as_int(run.get("id"))
        if run_id is None:
            continue
        runs.append(
            CanonicalTestRun(
                id=run_id,
                name=_as_str(run.get("name")),
                state=_as_str(run.get("state")),
                outcome=_as_str(run.get("outcome")),
                total_tests=_as_int(run.get("totalTests")),
                passed_tests=_as_int(run.get("passedTests")),
                failed_tests=_as_int(run.get("unanalyzedTests"))
                or _as_int(run.get("incompleteTests"))
                or _as_int(run.get("failedTests")),
                skipped_tests=_as_int(run.get("notApplicableTests"))
                or _as_int(run.get("notImpactedTests"))
                or _as_int(run.get("skippedTests")),
                started_at=_parse_datetime(run.get("startedDate")),
                completed_at=_parse_datetime(run.get("completedDate")),
                url=_as_str(run.get("url")),
                source_ref=f"raw.test_runs.value[{index}]",
            )
        )
    return runs


def _extract_test_results(
    raw_test_results: Any,
) -> tuple[list[CanonicalTestResult], list[CanonicalTestResult]]:
    test_results_payload = _as_dict(raw_test_results)
    bundles = _as_list(test_results_payload.get("value"))
    failed: list[CanonicalTestResult] = []
    warning: list[CanonicalTestResult] = []
    for bundle_index, bundle in enumerate(bundles):
        bundle_payload = _as_dict(bundle)
        run_id = _as_int(bundle_payload.get("run_id"))
        payload = _as_dict(bundle_payload.get("payload"))
        results = _as_list(payload.get("value"))
        for result_index, item in enumerate(results):
            result = _as_dict(item)
            outcome = _as_str(result.get("outcome"))
            outcome_lower = (outcome or "").lower()
            canonical = CanonicalTestResult(
                id=result.get("id") if isinstance(result.get("id"), (str, int)) else None,
                test_run_id=run_id,
                test_name=_as_str(result.get("testCaseTitle"))
                or _as_str(_as_dict(result.get("testCase")).get("name"))
                or _as_str(result.get("automatedTestName")),
                outcome=outcome,
                duration_ms=_as_float(result.get("durationInMs")),
                error_message=_as_str(result.get("errorMessage")),
                stack_trace=_as_str(result.get("stackTrace")),
                source_ref=f"raw.test_results.value[{bundle_index}].payload.value[{result_index}]",
            )
            if outcome_lower == "passed":
                continue
            if outcome_lower in _SKIPPED_TEST_OUTCOMES or not outcome_lower:
                warning.append(canonical)
            else:
                failed.append(canonical)
    return failed, warning


def _summarize_tests(
    test_runs: list[CanonicalTestRun],
    failed_tests: list[CanonicalTestResult],
    warning_tests: list[CanonicalTestResult],
) -> CanonicalTestSummary:
    total_runs = len(test_runs)
    total_tests = 0
    passed_tests = 0
    failed_tests_count = len(failed_tests)
    skipped_tests = len(warning_tests)
    for run in test_runs:
        if run.total_tests is not None:
            total_tests += run.total_tests
        if run.passed_tests is not None:
            passed_tests += run.passed_tests
        if run.failed_tests is not None and run.total_tests is None:
            failed_tests_count += run.failed_tests
        if run.skipped_tests is not None and run.total_tests is None:
            skipped_tests += run.skipped_tests
    if total_tests == 0 and (passed_tests or failed_tests_count or skipped_tests):
        total_tests = passed_tests + failed_tests_count + skipped_tests
    pass_rate = round(passed_tests / total_tests, 4) if total_tests > 0 else None
    return CanonicalTestSummary(
        total_runs=total_runs,
        total_tests=total_tests,
        passed_tests=passed_tests,
        failed_tests=failed_tests_count,
        skipped_tests=skipped_tests,
        pass_rate=pass_rate,
    )


def _normalize_quality_context(
    raw: dict[str, Any],
    execution_context: ExecutionContext,
) -> QualityContext:
    test_runs = _extract_test_runs(raw.get("test_runs"))
    failed_tests, warning_tests = _extract_test_results(raw.get("test_results"))
    summary = _summarize_tests(test_runs, failed_tests, warning_tests)

    missing: list[str] = []
    if not test_runs:
        missing.append("test_runs_missing")
    if not failed_tests and not warning_tests and summary.total_tests == 0:
        missing.append("test_results_missing")

    quality_signals = [
        f"total_tests={summary.total_tests}",
        f"passed_tests={summary.passed_tests}",
        f"failed_tests={summary.failed_tests}",
        f"skipped_tests={summary.skipped_tests}",
    ]
    quality_signals.extend(_unique_non_empty([item.test_name for item in failed_tests]))
    quality_signals.extend(_unique_non_empty([item.name for item in test_runs]))
    quality_signals.extend(missing)

    for task in execution_context.tasks:
        result = (task.result or "").lower()
        if result and result != "succeeded":
            quality_signals.append(f"timeline_non_success:{task.name}:{task.result}")
        if task.type and "warning" in task.type.lower():
            quality_signals.append(f"timeline_warning:{task.name}")

    scan_summary = CanonicalScanSummary(
        security_status=None,
        code_quality_status=None,
        dependency_status=None,
        scan_signals=[],
        missing_scan_context=["scan_tools_not_collected_in_phase_3"],
    )

    return QualityContext(
        test_runs=test_runs,
        test_summary=summary,
        failed_tests=failed_tests,
        warning_tests=warning_tests,
        scan_summary=scan_summary,
        quality_signals=_unique_non_empty(quality_signals),
        missing_quality_context=missing,
    )


def _risk_detection_terms() -> dict[str, list[str]]:
    return {
        "config": [
            "config",
            "configuration",
            "appsettings",
            "env",
            "environment variable",
            "yaml",
            "yml",
            "json",
            "secret",
            "settings",
        ],
        "database": [
            "database",
            " db ",
            "migration",
            "schema",
            "sql",
            "ddl",
            "liquibase",
            "flyway",
        ],
        "infra": [
            "terraform",
            "bicep",
            " arm ",
            "infrastructure",
            "infra",
            "helm",
            "kubernetes",
            "aks",
            "container app",
            "app service",
        ],
        "dependency": [
            "dependency",
            "package",
            "requirements",
            "pyproject",
            "poetry",
            "npm",
            "package-lock",
            "pom.xml",
            "gradle",
        ],
        "feature_flag": [
            "feature flag",
            "feature toggle",
            "launchdarkly",
            "flag",
        ],
    }


def _normalize_risk_context(
    run_context: RunContext,
    change_context: ChangeContext,
    execution_context: ExecutionContext,
    quality_context: QualityContext,
    raw_status: str | None,
) -> RiskContext:
    text_sources = _unique_non_empty(
        [work_item.title for work_item in change_context.work_items]
        + [work_item.description for work_item in change_context.work_items]
        + [pull_request.title for pull_request in change_context.pull_requests]
        + [pull_request.description for pull_request in change_context.pull_requests]
        + [commit.message for commit in change_context.commits]
        + [task.name for task in execution_context.tasks]
        + [job.name for job in execution_context.jobs]
        + [stage.name for stage in execution_context.stages]
        + [artifact.name for artifact in execution_context.artifacts]
    )
    combined_text = " | ".join(text_sources).lower()
    terms = _risk_detection_terms()

    config_change = _contains_any(combined_text, terms["config"])
    database_change = _contains_any(combined_text, terms["database"])
    infra_change = _contains_any(combined_text, terms["infra"])
    dependency_change = _contains_any(combined_text, terms["dependency"])
    feature_flag_change = _contains_any(combined_text, terms["feature_flag"])

    rollback_indicators = _unique_non_empty(
        [run_context.source_version, run_context.build_number]
        + [artifact.name for artifact in execution_context.artifacts]
        + [
            task.name
            for task in execution_context.tasks
            if _contains_any((task.name or "").lower(), _DEPLOYMENT_TERMS)
            and (task.result or "").lower() == "succeeded"
        ]
    )

    risk_signals: list[str] = []
    if quality_context.test_summary.failed_tests > 0:
        risk_signals.append(f"failed_tests={quality_context.test_summary.failed_tests}")
    for task in execution_context.tasks:
        result = (task.result or "").lower()
        if result and result != "succeeded":
            risk_signals.append(f"task_non_success:{task.name}:{task.result}")
    if raw_status and raw_status.lower() == "partial":
        risk_signals.append("raw_collection_partial")
    if "test_results_missing" in quality_context.missing_quality_context:
        risk_signals.append("missing_test_context")
    if config_change:
        risk_signals.append("config_change_detected")
    if database_change:
        risk_signals.append("database_change_detected")
    if infra_change:
        risk_signals.append("infrastructure_change_detected")
    if dependency_change:
        risk_signals.append("dependency_change_detected")
    if feature_flag_change:
        risk_signals.append("feature_flag_change_detected")

    missing_risk_context: list[str] = []
    if not text_sources:
        missing_risk_context.append("insufficient_change_execution_text")

    impacted_components = _unique_non_empty(
        [pull_request.source_branch for pull_request in change_context.pull_requests]
        + [work_item.area_path for work_item in change_context.work_items]
    )

    return RiskContext(
        impacted_components=impacted_components,
        config_change_detected=config_change,
        database_change_detected=database_change,
        infrastructure_change_detected=infra_change,
        dependency_change_detected=dependency_change,
        feature_flag_change_detected=feature_flag_change,
        rollback_indicators=rollback_indicators,
        risk_signals=_unique_non_empty(risk_signals),
        missing_risk_context=missing_risk_context,
    )


def _normalize_metadata(
    raw_bundle: dict[str, Any],
    raw_sections: dict[str, Any],
) -> NormalizationMetadata:
    errors = _as_list(raw_bundle.get("errors"))
    raw_collector_errors: list[str] = []
    for error in errors:
        payload = _as_dict(error)
        collector = _as_str(payload.get("collector")) or "unknown_collector"
        message = _as_str(payload.get("message")) or "unknown error"
        raw_collector_errors.append(f"{collector}: {message}")

    normalized_sections = [
        "run_context",
        "change_context",
        "execution_context",
        "quality_context",
        "risk_context",
    ]
    missing_sections = [
        f"raw.{name}"
        for name in (
            "build",
            "timeline",
            "artifacts",
            "work_item_refs",
            "work_items",
            "changes",
            "pull_requests",
            "test_runs",
            "test_results",
        )
        if not _as_dict(raw_sections).get(name)
    ]
    warnings: list[str] = []
    if missing_sections:
        warnings.append("some_raw_sections_missing")
    if raw_collector_errors:
        warnings.append("raw_collector_errors_present")
    return NormalizationMetadata(
        raw_collection_status=_as_str(raw_bundle.get("status")),
        raw_collector_errors=raw_collector_errors,
        normalized_sections=normalized_sections,
        missing_sections=missing_sections,
        warnings=warnings,
    )


def normalize_raw_bundle(
    raw_bundle: dict[str, Any],
    source_path: str | None = None,
) -> CanonicalDodDocument:
    """Normalize a Phase-2 raw bundle into canonical deterministic structure."""

    raw_sections = _as_dict(raw_bundle.get("raw"))
    build_payload = _as_dict(raw_sections.get("build"))

    bundle_build_id = _as_int(raw_bundle.get("build_id"))
    build_id = bundle_build_id or _as_int(build_payload.get("id")) or 0
    organization = _as_str(raw_bundle.get("organization")) or "unknown"
    project = _as_str(raw_bundle.get("project")) or "unknown"

    run_context = _normalize_run_context(build_payload, build_id)
    change_context = _normalize_change_context(raw_sections)
    execution_context = _normalize_execution_context(raw_sections)
    quality_context = _normalize_quality_context(raw_sections, execution_context)
    risk_context = _normalize_risk_context(
        run_context=run_context,
        change_context=change_context,
        execution_context=execution_context,
        quality_context=quality_context,
        raw_status=_as_str(raw_bundle.get("status")),
    )
    normalization_metadata = _normalize_metadata(raw_bundle, raw_sections)

    return CanonicalDodDocument(
        schema_version="1.0",
        build_id=build_id,
        organization=organization,
        project=project,
        generated_at=datetime.now(UTC),
        source_raw_bundle_path=source_path,
        run_context=run_context,
        change_context=change_context,
        execution_context=execution_context,
        quality_context=quality_context,
        risk_context=risk_context,
        normalization_metadata=normalization_metadata,
    )


def build_canonical_summary(document: CanonicalDodDocument, canonical_path: str) -> dict[str, Any]:
    """Build safe canonical summary payload for CLI/API responses."""

    risk_flags: list[str] = []
    if document.risk_context.config_change_detected:
        risk_flags.append("config_change_detected")
    if document.risk_context.database_change_detected:
        risk_flags.append("database_change_detected")
    if document.risk_context.infrastructure_change_detected:
        risk_flags.append("infrastructure_change_detected")
    if document.risk_context.dependency_change_detected:
        risk_flags.append("dependency_change_detected")
    if document.risk_context.feature_flag_change_detected:
        risk_flags.append("feature_flag_change_detected")

    return {
        "status": "completed",
        "message": "Canonical normalization completed.",
        "build_id": document.build_id,
        "pipeline_name": document.run_context.pipeline_name,
        "source_branch": document.run_context.source_branch,
        "source_version": document.run_context.source_version,
        "work_item_count": len(document.change_context.work_items),
        "commit_count": len(document.change_context.commits),
        "pull_request_count": len(document.change_context.pull_requests),
        "stage_count": len(document.execution_context.stages),
        "job_count": len(document.execution_context.jobs),
        "task_count": len(document.execution_context.tasks),
        "artifact_count": len(document.execution_context.artifacts),
        "test_run_count": len(document.quality_context.test_runs),
        "failed_test_count": len(document.quality_context.failed_tests),
        "risk_flags": risk_flags,
        "warnings": document.normalization_metadata.warnings,
        "canonical_path": canonical_path,
    }
