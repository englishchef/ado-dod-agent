"""Change-context collector for work-item, change, and PR metadata."""

from __future__ import annotations

from typing import Any

from app.clients.ado.base import AzureDevOpsClientError
from app.clients.ado.build_client import AzureDevOpsBuildClient
from app.clients.ado.git_client import AzureDevOpsGitClient
from app.clients.ado.workitem_client import AzureDevOpsWorkItemClient
from app.models.raw import CollectorError, CollectorState, CollectorStatus
from app.storage.local_store import LocalJsonStore


def _extract_work_item_ids(work_item_refs_payload: dict[str, Any]) -> list[int]:
    refs = work_item_refs_payload.get("value")
    if not isinstance(refs, list):
        return []

    result: list[int] = []
    for item in refs:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if isinstance(raw_id, int):
            result.append(raw_id)
            continue
        if isinstance(raw_id, str) and raw_id.isdigit():
            result.append(int(raw_id))
            continue
        url = item.get("url")
        if isinstance(url, str):
            trailing = url.rsplit("/", maxsplit=1)[-1]
            if trailing.isdigit():
                result.append(int(trailing))
    return sorted(set(result))


def _extract_pull_request_ids(payload: Any) -> list[int]:
    ids: list[int] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"pullRequestId", "pull_request_id"}:
                    if isinstance(value, int):
                        ids.append(value)
                    elif isinstance(value, str) and value.isdigit():
                        ids.append(int(value))
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(payload)
    return sorted(set(ids))


async def _hydrate_work_items(
    work_item_ids: list[int],
    work_item_client: AzureDevOpsWorkItemClient,
) -> dict[str, Any]:
    hydrated_values: list[Any] = []
    for index in range(0, len(work_item_ids), 200):
        chunk = work_item_ids[index : index + 200]
        response = await work_item_client.get_work_items_batch(chunk)
        values = response.get("value")
        if isinstance(values, list):
            hydrated_values.extend(values)
    return {"count": len(hydrated_values), "value": hydrated_values}


async def collect_change_context(
    build_id: int,
    include_pull_requests: bool,
    repository_id: str | None,
    commit_id: str | None,
    build_client: AzureDevOpsBuildClient,
    work_item_client: AzureDevOpsWorkItemClient,
    git_client: AzureDevOpsGitClient,
    store: LocalJsonStore,
) -> tuple[dict[str, Any], CollectorStatus, list[CollectorError], dict[str, str]]:
    """Collect work-item refs, changes, hydrated items, and PR metadata."""

    payload: dict[str, Any] = {}
    errors: list[CollectorError] = []
    artifact_paths: dict[str, str] = {}
    status: CollectorState = "completed"
    collected_count = 0

    try:
        work_item_refs = await build_client.get_build_work_items_refs(build_id)
        payload["work_item_refs"] = work_item_refs
        artifact_paths["work_item_refs"] = store.save_json(
            f"raw/{build_id}/work_item_refs.json",
            work_item_refs,
        )
        collected_count += 1
    except AzureDevOpsClientError as exc:
        status = "partial"
        work_item_refs = {"count": 0, "value": []}
        errors.append(
            CollectorError(
                collector="change_context",
                message=f"work item refs retrieval failed: {exc.summary}",
                severity="medium",
                status_code=exc.status_code,
                path=exc.path,
            )
        )

    try:
        changes = await build_client.get_build_changes(build_id)
        payload["changes"] = changes
        artifact_paths["changes"] = store.save_json(f"raw/{build_id}/changes.json", changes)
        collected_count += 1
    except AzureDevOpsClientError as exc:
        status = "partial"
        payload["changes"] = {"count": 0, "value": []}
        errors.append(
            CollectorError(
                collector="change_context",
                message=f"build changes retrieval failed: {exc.summary}",
                severity="medium",
                status_code=exc.status_code,
                path=exc.path,
            )
        )

    work_item_ids = _extract_work_item_ids(work_item_refs)
    if work_item_ids:
        try:
            work_items_payload = await _hydrate_work_items(work_item_ids, work_item_client)
            payload["work_items"] = work_items_payload
            artifact_paths["work_items"] = store.save_json(
                f"raw/{build_id}/work_items.json",
                work_items_payload,
            )
            collected_count += 1
        except AzureDevOpsClientError as exc:
            status = "partial"
            payload["work_items"] = {"count": 0, "value": []}
            errors.append(
                CollectorError(
                    collector="change_context",
                    message=f"work item hydration failed: {exc.summary}",
                    severity="medium",
                    status_code=exc.status_code,
                    path=exc.path,
                )
            )
    else:
        payload["work_items"] = {"count": 0, "value": []}
        artifact_paths["work_items"] = store.save_json(
            f"raw/{build_id}/work_items.json",
            payload["work_items"],
        )

    pull_requests_payload: dict[str, Any] = {"query": None, "pull_requests": [], "commits": {}}
    if include_pull_requests and repository_id and commit_id:
        try:
            query_payload = await git_client.get_pull_requests_for_commit(repository_id, commit_id)
            pull_requests_payload["query"] = query_payload
            pr_ids = _extract_pull_request_ids(query_payload)
            for pr_id in pr_ids:
                try:
                    pr_detail = await git_client.get_pull_request(repository_id, pr_id)
                    pull_requests_payload["pull_requests"].append(pr_detail)
                    pr_commits = await git_client.get_pull_request_commits(repository_id, pr_id)
                    pull_requests_payload["commits"][str(pr_id)] = pr_commits
                except AzureDevOpsClientError as exc:
                    status = "partial"
                    errors.append(
                        CollectorError(
                            collector="change_context",
                            message=f"pull request detail lookup failed: {exc.summary}",
                            severity="low",
                            status_code=exc.status_code,
                            path=exc.path,
                        )
                    )
            collected_count += 1
        except AzureDevOpsClientError as exc:
            status = "partial"
            errors.append(
                CollectorError(
                    collector="change_context",
                    message=f"pull request query failed: {exc.summary}",
                    severity="low",
                    status_code=exc.status_code,
                    path=exc.path,
                )
            )
    elif include_pull_requests:
        pull_requests_payload["query"] = {
            "reason": "repository_id_or_commit_id_missing",
        }
    else:
        pull_requests_payload["query"] = {"reason": "include_pull_requests_disabled"}

    payload["pull_requests"] = pull_requests_payload
    artifact_paths["pull_requests"] = store.save_json(
        f"raw/{build_id}/pull_requests.json",
        pull_requests_payload,
    )

    collector_status = CollectorStatus(
        name="change_context",
        status=status,
        records_collected=collected_count,
    )
    return payload, collector_status, errors, artifact_paths
