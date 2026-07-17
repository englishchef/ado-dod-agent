"""Service entry point for Phase 7A DoD agent orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.app.graphs.workflow import run_dod_workflow
from backend.app.models.run_summary import DodRunSummary, RunIssue
from backend.app.services.observability.langsmith_tracing import trace_dod_run
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.services.storage.storage_factory import get_storage_store
from backend.app.utils.config import get_settings


def run_dod_agent(input_data: dict[str, Any]) -> DodRunSummary:
    """Run the DoD agent workflow and return the persisted run summary model."""

    final_state = run_dod_workflow(input_data)
    summary_payload = final_state.get("run_summary")
    if not isinstance(summary_payload, dict) or not summary_payload:
        summary_payload = _load_persisted_summary(final_state)
    result_payload = summary_payload if isinstance(summary_payload, dict) else final_state
    duration_ms = result_payload.get("duration_ms") if isinstance(result_payload, dict) else None
    try:
        trace_dod_run(
            input_data=input_data,
            result=result_payload if isinstance(result_payload, dict) else {},
            timings={
                "duration_ms": duration_ms,
                "phase_durations_ms": final_state.get("phase_durations_ms"),
            },
            storage_backend=get_settings().DOD_STORAGE_BACKEND,
        )
    except Exception:
        pass
    if isinstance(summary_payload, dict):
        return DodRunSummary.model_validate(summary_payload)

    started_at = _parse_datetime(final_state.get("started_at")) or datetime.now(UTC)
    completed_at = _parse_datetime(final_state.get("completed_at"))
    return DodRunSummary(
        run_id=str(final_state.get("run_id", "")),
        build_id=int(final_state.get("build_id") or 0),
        organization=str(final_state.get("organization") or ""),
        project=str(final_state.get("project") or ""),
        status=str(final_state.get("status") or "failed"),
        started_at=started_at,
        completed_at=completed_at,
        service_now_payload=final_state.get("service_now_payload"),
        confidence=final_state.get("confidence"),
        artifact_paths=dict(final_state.get("artifact_paths") or {}),
        warnings=[RunIssue.model_validate(item) for item in final_state.get("warnings", [])],
        errors=[RunIssue.model_validate(item) for item in final_state.get("errors", [])],
    )


def _load_persisted_summary(final_state: dict[str, Any]) -> dict[str, Any] | None:
    """Load the persisted summary after the graph has compacted it out of state."""

    settings = get_settings()
    run_id = final_state.get("run_id")
    build_id = final_state.get("build_id")
    try:
        if settings.DOD_STORAGE_BACKEND == "local_json":
            store = LocalJsonStore(settings)
        else:
            store = get_storage_store(
                settings,
                run_id=str(run_id) if isinstance(run_id, str) else None,
            )
        lookup = run_id if isinstance(run_id, str) and run_id else int(build_id or 0)
        payload = store.load_run_summary(lookup)
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
