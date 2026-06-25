"""LangSmith tracing wrapper for DoD orchestration boundaries."""

from __future__ import annotations

import os
import warnings
from contextlib import redirect_stderr
from io import StringIO
from typing import Any

from backend.app.services.observability.redaction import (
    redact_dict,
    safe_run_summary_for_trace,
    safe_trace_metadata,
)
from backend.app.utils.config import get_settings

TRACE_MODE_METADATA_ONLY = "metadata_only"
TRACE_MODE_SUMMARY = "summary"
TRACE_MODE_DEBUG_REDACTED = "debug_redacted"
SUPPORTED_TRACE_MODES = {
    TRACE_MODE_METADATA_ONLY,
    TRACE_MODE_SUMMARY,
    TRACE_MODE_DEBUG_REDACTED,
}


def is_tracing_enabled() -> bool:
    """Return whether LangSmith tracing is explicitly enabled."""

    raw = os.environ.get("LANGSMITH_TRACING")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    alias = os.environ.get("TRACING_ENABLED")
    if alias is not None:
        return alias.strip().lower() in {"1", "true", "yes", "on"}
    return bool(get_settings().LANGSMITH_TRACING)


def get_trace_mode() -> str:
    """Return the configured DoD trace mode."""

    raw = os.environ.get("DOD_TRACE_MODE") or get_settings().DOD_TRACE_MODE
    mode = str(raw or TRACE_MODE_SUMMARY).strip().lower()
    if mode not in SUPPORTED_TRACE_MODES:
        return TRACE_MODE_SUMMARY
    return mode


def build_run_metadata(
    input_data: dict[str, Any] | None,
    result: dict[str, Any] | None,
    timings: dict[str, Any] | None,
    storage_backend: str | None,
) -> dict[str, Any]:
    """Build safe LangSmith metadata for one DoD run."""

    input_payload = input_data if isinstance(input_data, dict) else {}
    result_payload = result if isinstance(result, dict) else {}
    metadata = dict(input_payload.get("metadata") or {})
    rule_evaluation = result_payload.get("rule_evaluation")
    rule_summary = rule_evaluation.get("summary") if isinstance(rule_evaluation, dict) else {}
    confidence = result_payload.get("confidence")
    artifact_paths = result_payload.get("artifact_paths")
    errors = result_payload.get("errors")
    first_error = errors[0] if isinstance(errors, list) and errors else {}

    payload = {
        "run_id": result_payload.get("run_id"),
        "build_id": result_payload.get("build_id") or input_payload.get("build_id"),
        "organization": result_payload.get("organization") or input_payload.get("organization"),
        "project": result_payload.get("project") or input_payload.get("project"),
        "correlation_id": input_payload.get("correlation_id") or metadata.get("correlation_id"),
        "graph_name": get_settings().DOD_GRAPH_NAME,
        "assistant_name": get_settings().DOD_ASSISTANT_NAME,
        "storage_backend": storage_backend,
        "status": result_payload.get("status"),
        "rule_recommended_status": (
            rule_summary.get("recommended_status") if isinstance(rule_summary, dict) else None
        ),
        "highest_rule_severity": (
            rule_summary.get("highest_severity") if isinstance(rule_summary, dict) else None
        ),
        "final_confidence": confidence.get("overall") if isinstance(confidence, dict) else None,
        "test_completeness_score": (
            rule_evaluation.get("test_completeness_score")
            if isinstance(rule_evaluation, dict)
            else None
        ),
        "artifact_count": len(artifact_paths) if isinstance(artifact_paths, dict) else None,
        "duration_ms": _duration_ms(result_payload, timings),
        "phase_durations_ms": _phase_durations(timings),
        "error_code": first_error.get("code") if isinstance(first_error, dict) else None,
        "error_category": first_error.get("phase") if isinstance(first_error, dict) else None,
        "pipeline_id": metadata.get("pipeline_id") or input_payload.get("pipeline_id"),
        "pipeline_name": metadata.get("pipeline_name") or input_payload.get("pipeline_name"),
        "build_number": metadata.get("build_number") or input_payload.get("build_number"),
        "branch": metadata.get("branch") or input_payload.get("branch"),
        "requested_by": input_payload.get("requested_by") or metadata.get("requested_by"),
        "source": input_payload.get("source") or metadata.get("source"),
        "mode": result_payload.get("mode") or input_payload.get("mode"),
        "trace_mode": get_trace_mode(),
    }
    return safe_trace_metadata({key: value for key, value in payload.items() if value is not None})


def trace_event(name: str, metadata: dict[str, Any]) -> bool:
    """Send one small LangSmith event; return whether it was submitted."""

    if not is_tracing_enabled():
        return False
    safe_metadata = safe_trace_metadata(metadata)
    try:
        with warnings.catch_warnings(), redirect_stderr(StringIO()):
            warnings.simplefilter("ignore")
            client = _langsmith_client()
            if client is None:
                return False
            project_name = _project_name()
            client.create_run(
                name=name,
                run_type="chain",
                inputs={},
                outputs={},
                metadata=safe_metadata,
                project_name=project_name,
            )
        return True
    except Exception:
        return False


def trace_dod_run(
    input_data: dict[str, Any] | None,
    result: dict[str, Any] | None,
    timings: dict[str, Any] | None,
    storage_backend: str | None,
) -> None:
    """Trace one DoD run using safe metadata and redacted summaries only."""

    if not is_tracing_enabled():
        return
    result_payload = result if isinstance(result, dict) else {}
    metadata = build_run_metadata(input_data, result_payload, timings, storage_backend)
    mode = get_trace_mode()
    if mode == TRACE_MODE_SUMMARY:
        metadata["summary"] = safe_run_summary_for_trace(result_payload)
    elif mode == TRACE_MODE_DEBUG_REDACTED:
        metadata["summary"] = safe_run_summary_for_trace(result_payload)
        metadata["debug"] = redact_dict(
            {
                "input": input_data or {},
                "result": result_payload,
            }
        )
    trace_event("dod run", metadata)


def safe_trace_context(
    input_data: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    timings: dict[str, Any] | None = None,
    storage_backend: str | None = None,
) -> dict[str, Any]:
    """Return safe trace context for callers that need metadata but not side effects."""

    return build_run_metadata(input_data, result, timings, storage_backend)


def _langsmith_client() -> Any | None:
    try:
        from langsmith import Client  # type: ignore[import-untyped]
    except Exception:
        return None

    kwargs: dict[str, Any] = {}
    endpoint = os.environ.get("LANGSMITH_ENDPOINT") or get_settings().LANGSMITH_ENDPOINT
    if endpoint:
        kwargs["api_url"] = endpoint
    return Client(**kwargs)


def _project_name() -> str:
    return os.environ.get("LANGSMITH_PROJECT") or get_settings().LANGSMITH_PROJECT


def _duration_ms(result: dict[str, Any], timings: dict[str, Any] | None) -> Any:
    if result.get("duration_ms") is not None:
        return result.get("duration_ms")
    if isinstance(timings, dict):
        return timings.get("duration_ms")
    return None


def _phase_durations(timings: dict[str, Any] | None) -> Any:
    if not isinstance(timings, dict):
        return None
    value = timings.get("phase_durations_ms") or timings.get("phase_timings_ms")
    return value if isinstance(value, dict) else None
