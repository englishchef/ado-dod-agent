"""Quality-context collector for test run/result metadata."""

from __future__ import annotations

from typing import Any

from app.clients.ado.base import AzureDevOpsClientError
from app.clients.ado.test_client import AzureDevOpsTestClient
from app.models.raw import CollectorError, CollectorState, CollectorStatus
from app.storage.local_store import LocalJsonStore


async def collect_quality_context(
    build_id: int,
    include_tests: bool,
    max_test_results_per_run: int,
    test_client: AzureDevOpsTestClient,
    store: LocalJsonStore,
) -> tuple[dict[str, Any], CollectorStatus, list[CollectorError], dict[str, str]]:
    """Collect test runs and test results with partial-failure handling."""

    payload: dict[str, Any] = {}
    errors: list[CollectorError] = []
    artifact_paths: dict[str, str] = {}

    if not include_tests:
        status = CollectorStatus(
            name="quality_context",
            status="skipped",
            records_collected=0,
            skipped_reason="include_tests_disabled",
        )
        payload["test_runs"] = {"count": 0, "value": []}
        payload["test_results"] = {"count": 0, "value": [], "continuation_tokens": []}
        artifact_paths["test_runs"] = store.save_json(
            f"raw/{build_id}/test_runs.json",
            payload["test_runs"],
        )
        artifact_paths["test_results"] = store.save_json(
            f"raw/{build_id}/test_results.json",
            payload["test_results"],
        )
        return payload, status, errors, artifact_paths

    status_value: CollectorState = "completed"
    collected_count = 0

    try:
        test_runs = await test_client.get_test_runs(build_id)
        payload["test_runs"] = test_runs
        artifact_paths["test_runs"] = store.save_json(f"raw/{build_id}/test_runs.json", test_runs)
        collected_count += 1
    except AzureDevOpsClientError as exc:
        status_value = "partial"
        payload["test_runs"] = {"count": 0, "value": []}
        payload["test_results"] = {"count": 0, "value": [], "continuation_tokens": []}
        artifact_paths["test_runs"] = store.save_json(
            f"raw/{build_id}/test_runs.json",
            payload["test_runs"],
        )
        artifact_paths["test_results"] = store.save_json(
            f"raw/{build_id}/test_results.json",
            payload["test_results"],
        )
        errors.append(
            CollectorError(
                collector="quality_context",
                message=f"test runs retrieval failed: {exc.summary}",
                severity="low",
                status_code=exc.status_code,
                path=exc.path,
            )
        )
        status = CollectorStatus(
            name="quality_context",
            status=status_value,
            records_collected=collected_count,
        )
        return payload, status, errors, artifact_paths

    test_run_values = payload["test_runs"].get("value")
    run_ids: list[int] = []
    if isinstance(test_run_values, list):
        for item in test_run_values:
            if isinstance(item, dict) and isinstance(item.get("id"), int):
                run_ids.append(item["id"])

    results_payload: dict[str, Any] = {"count": 0, "value": [], "continuation_tokens": []}
    for run_id in run_ids:
        try:
            run_results = await test_client.get_test_results(run_id, max_test_results_per_run)
            results_payload["value"].append({"run_id": run_id, "payload": run_results})
            continuation_token = run_results.get("continuationToken")
            if continuation_token is not None:
                results_payload["continuation_tokens"].append(
                    {"run_id": run_id, "token": continuation_token}
                )
        except AzureDevOpsClientError as exc:
            status_value = "partial"
            errors.append(
                CollectorError(
                    collector="quality_context",
                    message=f"test results retrieval failed for run {run_id}: {exc.summary}",
                    severity="low",
                    status_code=exc.status_code,
                    path=exc.path,
                )
            )

    results_payload["count"] = len(results_payload["value"])
    payload["test_results"] = results_payload
    artifact_paths["test_results"] = store.save_json(
        f"raw/{build_id}/test_results.json",
        results_payload,
    )
    collected_count += 1

    status = CollectorStatus(
        name="quality_context",
        status=status_value,
        records_collected=collected_count,
    )
    return payload, status, errors, artifact_paths
