"""Execution-context collector for timeline and artifact metadata."""

from __future__ import annotations

from typing import Any

from backend.app.models.raw import CollectorError, CollectorState, CollectorStatus
from backend.app.services.ado.base import AzureDevOpsClientError
from backend.app.services.ado.build_client import AzureDevOpsBuildClient
from backend.app.services.storage.local_store import LocalJsonStore


async def collect_execution_context(
    build_id: int,
    include_artifacts: bool,
    build_client: AzureDevOpsBuildClient,
    store: LocalJsonStore,
) -> tuple[dict[str, Any], CollectorStatus, list[CollectorError], dict[str, str]]:
    """Collect timeline and artifacts with safe partial-failure behavior."""

    payload: dict[str, Any] = {}
    errors: list[CollectorError] = []
    artifact_paths: dict[str, str] = {}
    status: CollectorState = "completed"
    collected_count = 0

    try:
        timeline_payload = await build_client.get_build_timeline(build_id)
        payload["timeline"] = timeline_payload
        artifact_paths["timeline"] = store.save_json(
            f"raw/{build_id}/timeline.json",
            timeline_payload,
        )
        collected_count += 1
    except AzureDevOpsClientError as exc:
        status = "partial"
        errors.append(
            CollectorError(
                collector="execution_context",
                message=f"timeline retrieval failed: {exc.summary}",
                severity="high",
                status_code=exc.status_code,
                path=exc.path,
            )
        )

    if include_artifacts:
        try:
            artifacts_payload = await build_client.get_build_artifacts(build_id)
            payload["artifacts"] = artifacts_payload
            artifact_paths["artifacts"] = store.save_json(
                f"raw/{build_id}/artifacts.json",
                artifacts_payload,
            )
            collected_count += 1
        except AzureDevOpsClientError as exc:
            status = "partial"
            errors.append(
                CollectorError(
                    collector="execution_context",
                    message=f"artifact retrieval failed: {exc.summary}",
                    severity="medium",
                    status_code=exc.status_code,
                    path=exc.path,
                )
            )

    collector_status = CollectorStatus(
        name="execution_context",
        status=status,
        records_collected=collected_count,
    )
    return payload, collector_status, errors, artifact_paths

