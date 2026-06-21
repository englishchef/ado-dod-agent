"""Run-context collector for mandatory build metadata."""

from __future__ import annotations

from typing import Any

from backend.app.models.raw import CollectorError, CollectorStatus
from backend.app.services.ado.base import AzureDevOpsClientError
from backend.app.services.ado.build_client import AzureDevOpsBuildClient
from backend.app.services.storage.artifact_store import ArtifactStore


async def collect_run_context(
    build_id: int,
    build_client: AzureDevOpsBuildClient,
    store: ArtifactStore,
) -> tuple[dict[str, Any], CollectorStatus, list[CollectorError], dict[str, str]]:
    """Collect mandatory build metadata; raise on failure."""

    try:
        build_payload = await build_client.get_build(build_id)
    except AzureDevOpsClientError as exc:
        error = CollectorError(
            collector="run_context",
            message=f"build retrieval failed: {exc.summary}",
            severity="high",
            status_code=exc.status_code,
            path=exc.path,
        )
        raise RuntimeError(error.model_dump_json()) from exc

    build_path = store.save_json(f"raw/{build_id}/build.json", build_payload)
    status = CollectorStatus(
        name="run_context",
        status="completed",
        records_collected=1,
    )
    return {"build": build_payload}, status, [], {"build": build_path}

