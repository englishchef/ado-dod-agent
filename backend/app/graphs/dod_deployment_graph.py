"""LangGraph deployment adapter for the DoD agent."""

from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from backend.app.graphs.dod_deployment_state import DoDGraphState, normalize_dod_input
from backend.app.models.dod_contracts import (
    normalize_dod_run_input,
    serialize_dod_run_output,
)
from backend.app.services.observability.langsmith_tracing import safe_trace_context, trace_event
from backend.app.services.orchestration.dod_run_service import run_dod_agent
from backend.app.utils.config import get_settings
from backend.app.utils.logging import get_logger
from backend.app.utils.state_serialization import (
    GraphStateValidationError,
    exception_type_chain,
    validate_graph_state,
)

logger = get_logger(__name__)


def make_graph_dod() -> Any:
    """Compile the enterprise LangGraph deployment graph for the DoD assistant."""

    graph = StateGraph(DoDGraphState)
    graph.add_node("run_dod", _run_dod_node)
    graph.add_edge(START, "run_dod")
    graph.add_edge("run_dod", END)
    return graph.compile()


def _run_dod_node(state: DoDGraphState) -> DoDGraphState:
    try:
        normalized = normalize_dod_input(state)
        _validate_deployment_state(normalized, "enterprise_input")
    except GraphStateValidationError as exc:
        return _deployment_state_failure(state, exc, "input")
    contract_input = normalize_dod_run_input(normalized)
    request = contract_input.model_dump(mode="json")
    try:
        output = serialize_dod_run_output(run_dod_agent(request), fallback_input=contract_input)
    except Exception as exc:
        logger.error(
            "dod deployment node failed exception_chain=%s",
            exception_type_chain(exc),
        )
        return cast(DoDGraphState, {
            **normalized,
            "status": "failed",
            "current_phase": "run_dod",
            "service_now_payload": None,
            "confidence": None,
            "rule_evaluation_summary": None,
            "warnings": [],
            "errors": [
                {
                    "severity": "error",
                    "code": "dod_run_failed",
                    "message": "The DoD run could not be completed.",
                    "phase": "run_dod",
                    "diagnostics": {"exception_type": type(exc).__name__},
                }
            ],
            "result": None,
        })
    result = cast(DoDGraphState, {
        **normalized,
        **output.model_dump(mode="json"),
        "current_phase": "completed",
    })
    try:
        diagnostics = _validate_deployment_state(result, "enterprise_output")
    except GraphStateValidationError as exc:
        return _deployment_state_failure(result, exc, "run_dod")
    if diagnostics.get("warning_required"):
        result["warnings"] = [
            *list(result.get("warnings") or []),
            {
                "severity": "warning",
                "code": "GRAPH_STATE_SIZE_WARNING",
                "message": "Graph state exceeded the configured warning threshold.",
                "phase": "run_dod",
                "diagnostics": {
                    "state_size_bytes": diagnostics.get("state_size_bytes"),
                    "warn_bytes": diagnostics.get("warn_bytes"),
                    "largest_keys": diagnostics.get("largest_keys"),
                },
            },
        ]
    trace_event(
        "dod graph output serialization",
        safe_trace_context(
            input_data=request,
            result=result,
            storage_backend=None,
        ),
    )

    return result


def _validate_deployment_state(state: DoDGraphState, context: str) -> dict[str, Any]:
    settings = get_settings()
    return validate_graph_state(
        state,
        context=context,
        warn_bytes=int(settings.DOD_GRAPH_STATE_WARN_BYTES),
        max_bytes=int(settings.DOD_GRAPH_STATE_MAX_BYTES),
    )


def _deployment_state_failure(
    state: DoDGraphState,
    exc: GraphStateValidationError,
    phase: str,
) -> DoDGraphState:
    diagnostics = exc.diagnostics
    return cast(DoDGraphState, {
        "organization": state.get("organization")
        if isinstance(state.get("organization"), str)
        else "",
        "project": state.get("project") if isinstance(state.get("project"), str) else "",
        "build_id": state.get("build_id") if isinstance(state.get("build_id"), int) else 0,
        "mode": state.get("mode") if isinstance(state.get("mode"), str) else "pipeline",
        "correlation_id": state.get("correlation_id")
        if isinstance(state.get("correlation_id"), str)
        else None,
        "requested_by": None,
        "source": None,
        "metadata": {},
        "run_id": state.get("run_id") if isinstance(state.get("run_id"), str) else None,
        "status": "failed",
        "current_phase": phase,
        "service_now_payload": None,
        "confidence": None,
        "rule_evaluation_summary": None,
        "artifact_paths": {
            str(key): value
            for key, value in dict(state.get("artifact_paths") or {}).items()
            if isinstance(key, str) and isinstance(value, str)
        },
        "warnings": [],
        "errors": [
            {
                "severity": "error",
                "code": exc.code,
                "message": "Graph state could not be persisted safely.",
                "phase": phase,
                "diagnostics": {
                    "state_size_bytes": diagnostics.get("state_size_bytes"),
                    "largest_keys": diagnostics.get("largest_keys"),
                    "non_serializable_paths": diagnostics.get("non_serializable_paths"),
                },
            }
        ],
        "result": None,
    })
