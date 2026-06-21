"""Coordinator for Phase-2 raw metadata collection."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.app.models.inputs import CollectRawInput, GenerateRunInput
from backend.app.models.raw import (
    CollectionStatus,
    CollectorError,
    CollectorStatus,
    RawArtifactPaths,
    RawCollectionResult,
    RawCollectionSummary,
)
from backend.app.services.ado.base import AzureDevOpsClientConfig
from backend.app.services.ado.build_client import AzureDevOpsBuildClient
from backend.app.services.ado.git_client import AzureDevOpsGitClient
from backend.app.services.ado.test_client import AzureDevOpsTestClient
from backend.app.services.ado.workitem_client import AzureDevOpsWorkItemClient
from backend.app.services.auth.ado_token_provider import AzureDevOpsTokenProvider
from backend.app.services.collectors.change_context import collect_change_context
from backend.app.services.collectors.execution_context import collect_execution_context
from backend.app.services.collectors.quality_context import collect_quality_context
from backend.app.services.collectors.run_context import collect_run_context
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.services.storage.storage_factory import get_storage_store
from backend.app.utils.config import get_settings
from backend.app.utils.logging import get_logger

logger = get_logger(__name__)


def _as_collect_input(input_model: CollectRawInput | GenerateRunInput) -> CollectRawInput:
    if isinstance(input_model, CollectRawInput):
        return input_model
    return CollectRawInput.model_validate(input_model.model_dump())


def _count_from_value_list(payload: Any) -> int:
    if isinstance(payload, dict):
        value = payload.get("value")
        if isinstance(value, list):
            return len(value)
    return 0


def _summarize(raw: dict[str, Any]) -> RawCollectionSummary:
    timeline = raw.get("timeline", {})
    timeline_records = timeline.get("records") if isinstance(timeline, dict) else None

    pull_requests = raw.get("pull_requests", {})
    pr_items = pull_requests.get("pull_requests") if isinstance(pull_requests, dict) else None

    test_results = raw.get("test_results", {})
    test_result_values = test_results.get("value") if isinstance(test_results, dict) else None

    return RawCollectionSummary(
        timeline_record_count=len(timeline_records) if isinstance(timeline_records, list) else 0,
        artifact_count=_count_from_value_list(raw.get("artifacts", {})),
        work_item_ref_count=_count_from_value_list(raw.get("work_item_refs", {})),
        work_item_count=_count_from_value_list(raw.get("work_items", {})),
        change_count=_count_from_value_list(raw.get("changes", {})),
        pull_request_count=len(pr_items) if isinstance(pr_items, list) else 0,
        test_run_count=_count_from_value_list(raw.get("test_runs", {})),
        test_result_count=len(test_result_values) if isinstance(test_result_values, list) else 0,
    )


async def collect_raw_metadata(
    input_model: CollectRawInput | GenerateRunInput,
) -> RawCollectionResult:
    """Collect and persist raw Azure DevOps metadata for a build."""

    request = _as_collect_input(input_model)
    settings = get_settings()
    store = (
        LocalJsonStore(settings)
        if settings.DOD_STORAGE_BACKEND == "local_json"
        else get_storage_store(settings)
    )
    store.ensure_run_dirs(request.build_id)

    collected_at = datetime.now(UTC)
    timestamp = collected_at.strftime("%Y%m%dT%H%M%SZ")
    collection_run_id = f"dod-raw-{timestamp}-{request.build_id}"

    token_provider = AzureDevOpsTokenProvider(settings=settings)
    client_config = AzureDevOpsClientConfig(
        organization=request.organization,
        project=request.project,
        api_version=settings.ADO_API_VERSION,
    )

    build_client = AzureDevOpsBuildClient(client_config, token_provider)
    workitem_client = AzureDevOpsWorkItemClient(client_config, token_provider)
    git_client = AzureDevOpsGitClient(client_config, token_provider)
    test_client = AzureDevOpsTestClient(client_config, token_provider)

    collector_statuses: list[CollectorStatus] = []
    errors: list[CollectorError] = []
    artifact_path_map: dict[str, str] = {}
    raw: dict[str, Any] = {}

    try:
        # 1) Mandatory run context
        try:
            run_raw, run_status, run_errors, run_paths = await collect_run_context(
                build_id=request.build_id,
                build_client=build_client,
                store=store,
            )
        except RuntimeError as exc:
            try:
                failure_error = CollectorError.model_validate_json(str(exc))
            except Exception:
                failure_error = CollectorError(
                    collector="run_context",
                    message="build retrieval failed",
                    severity="high",
                )
            errors.append(failure_error)
            failed_result = RawCollectionResult(
                collection_run_id=collection_run_id,
                build_id=request.build_id,
                status="failed",
                collected_at=collected_at,
                summary=RawCollectionSummary(),
                artifact_paths=RawArtifactPaths(),
                collector_statuses=[
                    CollectorStatus(
                        name="run_context",
                        status="failed",
                        records_collected=0,
                    )
                ],
                errors=errors,
            )
            bundle_payload = {
                "collection_run_id": collection_run_id,
                "build_id": request.build_id,
                "organization": request.organization,
                "project": request.project,
                "collected_at": collected_at,
                "status": "failed",
                "collector_statuses": [
                    item.model_dump() for item in failed_result.collector_statuses
                ],
                "errors": [item.model_dump() for item in errors],
                "raw": {},
            }
            raw_bundle_path = store.save_json(
                f"raw/{request.build_id}/raw_bundle.json",
                bundle_payload,
            )
            failed_result.artifact_paths.raw_bundle = raw_bundle_path
            return failed_result

        raw.update(run_raw)
        collector_statuses.append(run_status)
        errors.extend(run_errors)
        artifact_path_map.update(run_paths)

        build_payload = raw.get("build", {})
        build_repo = build_payload.get("repository") if isinstance(build_payload, dict) else None
        repository_id = request.repository
        if not repository_id and isinstance(build_repo, dict):
            repo_candidate = build_repo.get("id")
            if isinstance(repo_candidate, str):
                repository_id = repo_candidate

        commit_id = None
        if isinstance(build_payload, dict):
            commit_candidate = build_payload.get("sourceVersion")
            if isinstance(commit_candidate, str):
                commit_id = commit_candidate

        # 2) Execution context
        (
            execution_raw,
            execution_status,
            execution_errors,
            execution_paths,
        ) = await collect_execution_context(
            build_id=request.build_id,
            include_artifacts=request.include_artifacts,
            build_client=build_client,
            store=store,
        )
        raw.update(execution_raw)
        collector_statuses.append(execution_status)
        errors.extend(execution_errors)
        artifact_path_map.update(execution_paths)

        # 3) Change context
        change_raw, change_status, change_errors, change_paths = await collect_change_context(
            build_id=request.build_id,
            include_pull_requests=request.include_pull_requests,
            repository_id=repository_id,
            commit_id=commit_id,
            build_client=build_client,
            work_item_client=workitem_client,
            git_client=git_client,
            store=store,
        )
        raw.update(change_raw)
        collector_statuses.append(change_status)
        errors.extend(change_errors)
        artifact_path_map.update(change_paths)

        # 4) Quality context
        quality_raw, quality_status, quality_errors, quality_paths = await collect_quality_context(
            build_id=request.build_id,
            include_tests=request.include_tests,
            max_test_results_per_run=request.max_test_results_per_run,
            test_client=test_client,
            store=store,
        )
        raw.update(quality_raw)
        collector_statuses.append(quality_status)
        errors.extend(quality_errors)
        artifact_path_map.update(quality_paths)

        # Ensure bundle contains all expected top-level raw sections.
        raw.setdefault("build", {})
        raw.setdefault("timeline", {})
        raw.setdefault("artifacts", {})
        raw.setdefault("work_item_refs", {})
        raw.setdefault("work_items", {})
        raw.setdefault("changes", {})
        raw.setdefault("pull_requests", {})
        raw.setdefault("test_runs", {})
        raw.setdefault("test_results", {})

        overall_status: CollectionStatus = "completed"
        if errors or any(item.status in {"partial", "failed"} for item in collector_statuses):
            overall_status = "partial"

        summary = _summarize(raw)
        definition = build_payload.get("definition") if isinstance(build_payload, dict) else None
        pipeline_name = definition.get("name") if isinstance(definition, dict) else None
        branch = build_payload.get("sourceBranch") if isinstance(build_payload, dict) else None
        build_status = build_payload.get("status") if isinstance(build_payload, dict) else None
        build_result = build_payload.get("result") if isinstance(build_payload, dict) else None
        bundle_payload = {
            "collection_run_id": collection_run_id,
            "build_id": request.build_id,
            "organization": request.organization,
            "project": request.project,
            "collected_at": collected_at,
            "status": overall_status,
            "collector_statuses": [item.model_dump() for item in collector_statuses],
            "errors": [item.model_dump() for item in errors],
            "raw": raw,
        }
        artifact_path_map["raw_bundle"] = store.save_json(
            f"raw/{request.build_id}/raw_bundle.json",
            bundle_payload,
        )

        return RawCollectionResult(
            collection_run_id=collection_run_id,
            build_id=request.build_id,
            status=overall_status,
            collected_at=collected_at,
            pipeline_name=pipeline_name if isinstance(pipeline_name, str) else None,
            branch=branch if isinstance(branch, str) else None,
            build_status=build_status if isinstance(build_status, str) else None,
            build_result=build_result if isinstance(build_result, str) else None,
            summary=summary,
            artifact_paths=RawArtifactPaths.model_validate(artifact_path_map),
            collector_statuses=collector_statuses,
            errors=errors,
        )
    finally:
        logger.info("raw_collection_complete build_id=%s", request.build_id)
        await build_client.aclose()
        await workitem_client.aclose()
        await git_client.aclose()
        await test_client.aclose()

