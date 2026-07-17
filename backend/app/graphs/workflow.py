"""Phase 7B LangGraph workflow assembly."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from backend.app.graphs.nodes import (
    assemble_run_result_node,
    assess_evidence_quality_node,
    assess_risk_tier_node,
    build_evidence_buckets_node,
    collect_raw_metadata_node,
    evaluate_rules_node,
    generate_llm_outputs_node,
    normalize_canonical_node,
    persist_routing_decisions_node,
    persist_run_summary_node,
    select_prompt_strategy_node,
    validate_input_node,
    validate_outputs_node,
)
from backend.app.graphs.state import (
    GRAPH_STATE_KEYS,
    LEGACY_LARGE_STATE_KEYS,
    STATUS_FAILED,
    DodGraphState,
)
from backend.app.services.observability.langsmith_tracing import trace_event
from backend.app.utils.config import get_settings
from backend.app.utils.logging import get_logger
from backend.app.utils.state_serialization import (
    GraphStateUnsupportedTypeError,
    GraphStateValidationError,
    exception_type_chain,
    graph_state_diagnostics,
    validate_graph_state,
)

Route = Literal["failed", "continue"]
NodeFunc = Callable[[DodGraphState], DodGraphState]
logger = get_logger(__name__)


def build_dod_workflow() -> Any:
    """Build the Phase 7B advanced-routing DoD orchestration graph."""

    graph = StateGraph(DodGraphState)
    graph.add_node("validate_input", _timed_node("input_normalization", validate_input_node))
    graph.add_node(
        "collect_raw_metadata",
        _timed_node("ado_metadata_collection", collect_raw_metadata_node),
    )
    graph.add_node(
        "normalize_canonical",
        _timed_node("canonical_normalization", normalize_canonical_node),
    )
    graph.add_node(
        "build_evidence_buckets",
        _timed_node("evidence_generation", build_evidence_buckets_node),
    )
    graph.add_node(
        "assess_evidence_quality",
        _timed_node("evidence_quality_assessment", assess_evidence_quality_node),
    )
    graph.add_node("assess_risk_tier", _timed_node("risk_tier_assessment", assess_risk_tier_node))
    graph.add_node(
        "select_prompt_strategy",
        _timed_node("prompt_strategy_selection", select_prompt_strategy_node),
    )
    graph.add_node(
        "generate_llm_outputs",
        _timed_node("llm_bucket_generation", generate_llm_outputs_node),
    )
    graph.add_node(
        "validate_outputs",
        _timed_node("validation_repair_payload_formatting", validate_outputs_node),
    )
    graph.add_node("evaluate_rules", _timed_node("rule_evaluation", evaluate_rules_node))
    graph.add_node(
        "assemble_run_result",
        _timed_node("final_output_serialization", assemble_run_result_node),
    )
    graph.add_node(
        "persist_routing_decisions",
        _timed_node("routing_persistence", persist_routing_decisions_node),
    )
    graph.add_node(
        "persist_run_summary",
        _timed_node("run_summary_persistence", persist_run_summary_node),
    )

    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges(
        "validate_input",
        route_after_validate_input,
        {"failed": "persist_run_summary", "continue": "collect_raw_metadata"},
    )
    graph.add_conditional_edges(
        "collect_raw_metadata",
        route_after_collect_raw,
        {"failed": "persist_run_summary", "continue": "normalize_canonical"},
    )
    graph.add_conditional_edges(
        "normalize_canonical",
        route_after_normalize,
        {"failed": "persist_run_summary", "continue": "build_evidence_buckets"},
    )
    graph.add_conditional_edges(
        "build_evidence_buckets",
        route_after_evidence,
        {"failed": "persist_run_summary", "continue": "assess_evidence_quality"},
    )
    graph.add_edge("assess_evidence_quality", "assess_risk_tier")
    graph.add_edge("assess_risk_tier", "select_prompt_strategy")
    graph.add_edge("select_prompt_strategy", "generate_llm_outputs")
    graph.add_conditional_edges(
        "generate_llm_outputs",
        route_after_llm,
        {"failed": "persist_routing_decisions", "continue": "validate_outputs"},
    )
    graph.add_edge("validate_outputs", "evaluate_rules")
    graph.add_edge("evaluate_rules", "assemble_run_result")
    graph.add_edge("assemble_run_result", "persist_routing_decisions")
    graph.add_edge("persist_routing_decisions", "persist_run_summary")
    graph.add_edge("persist_run_summary", END)
    return graph.compile()


def run_dod_workflow(input_data: dict[str, Any]) -> dict[str, Any]:
    """Run the Phase 7A workflow and return final graph state."""

    from backend.app.utils.state_serialization import to_json_safe

    normalized_input = to_json_safe(input_data, context="input")
    initial_state: DodGraphState = {
        "input": dict(normalized_input),
        "current_phase": "input",
        "artifact_paths": {},
        "phase_durations_ms": {},
        "warnings": [],
        "errors": [],
        "routing_decisions": [],
    }
    result = build_dod_workflow().invoke(initial_state)
    return dict(result)


def route_after_validate_input(state: DodGraphState) -> Route:
    return _route_failed_or_continue(state)


def route_after_collect_raw(state: DodGraphState) -> Route:
    return _route_failed_or_continue(state)


def route_after_normalize(state: DodGraphState) -> Route:
    return _route_failed_or_continue(state)


def route_after_evidence(state: DodGraphState) -> Route:
    return _route_failed_or_continue(state)


def route_after_llm(state: DodGraphState) -> Route:
    return _route_failed_or_continue(state)


def _route_failed_or_continue(state: DodGraphState) -> Route:
    return "failed" if state.get("status") == STATUS_FAILED else "continue"


def _timed_node(phase_name: str, node: NodeFunc) -> NodeFunc:
    def run(state: DodGraphState) -> DodGraphState:
        if phase_name == "canonical_normalization":
            _log_state_diagnostics(state, f"{phase_name}_before")
        try:
            _validate_checkpoint_state(state, f"{phase_name}_before")
        except GraphStateValidationError as exc:
            return _compact_guard_failure(state, phase_name, exc, duration_ms=0)

        started = perf_counter()
        try:
            update = node(state)
        except Exception as exc:
            logger.error(
                "graph node raised phase=%s exception_chain=%s",
                phase_name,
                exception_type_chain(exc),
            )
            validation_error = GraphStateUnsupportedTypeError(
                f"{phase_name} raised before producing a checkpoint-safe update.",
                {
                    "phase": phase_name,
                    "exception_type": type(exc).__name__,
                    **graph_state_diagnostics(state, phase=phase_name),
                },
            )
            duration_ms = int((perf_counter() - started) * 1000)
            return _compact_guard_failure(state, phase_name, validation_error, duration_ms)
        duration_ms = int((perf_counter() - started) * 1000)
        if not isinstance(update, dict):
            invalid_update = GraphStateUnsupportedTypeError(
                f"{phase_name} returned a non-dictionary state update.",
                {
                    "phase": phase_name,
                    "python_type": type(update).__name__,
                },
            )
            return _compact_guard_failure(state, phase_name, invalid_update, duration_ms)
        unexpected_keys = sorted(str(key) for key in update if key not in GRAPH_STATE_KEYS)
        if unexpected_keys:
            invalid_update = GraphStateUnsupportedTypeError(
                f"{phase_name} returned keys outside the graph-state contract.",
                {
                    "phase": phase_name,
                    "unexpected_keys": unexpected_keys,
                },
            )
            return _compact_guard_failure(state, phase_name, invalid_update, duration_ms)
        phase_durations = dict(state.get("phase_durations_ms") or {})
        phase_durations[phase_name] = duration_ms
        merged: DodGraphState = {
            **update,
            "phase_durations_ms": phase_durations,
            "current_phase": str(update.get("current_phase") or phase_name),
        }
        projected: DodGraphState = {**state, **merged}
        try:
            diagnostics = _validate_checkpoint_state(projected, f"{phase_name}_after")
        except GraphStateValidationError as exc:
            return _compact_guard_failure(state, phase_name, exc, duration_ms)
        if diagnostics.get("warning_required"):
            warning = {
                "severity": "warning",
                "code": "GRAPH_STATE_SIZE_WARNING",
                "message": "Graph state exceeded the configured warning threshold.",
                "phase": phase_name,
                "diagnostics": _compact_diagnostics(diagnostics),
            }
            warnings = list(merged.get("warnings") or state.get("warnings") or [])
            if not any(
                isinstance(item, dict)
                and item.get("code") == "GRAPH_STATE_SIZE_WARNING"
                and item.get("phase") == phase_name
                for item in warnings
            ):
                warnings.append(warning)
            merged["warnings"] = warnings
            projected = {**state, **merged}
            try:
                _validate_checkpoint_state(projected, f"{phase_name}_after_warning")
            except GraphStateValidationError as exc:
                return _compact_guard_failure(state, phase_name, exc, duration_ms)
        if phase_name == "canonical_normalization":
            _log_state_diagnostics(projected, f"{phase_name}_after")
        trace_event(
            f"dod {phase_name}",
            {
                "run_id": update.get("run_id") or state.get("run_id"),
                "build_id": update.get("build_id") or state.get("build_id"),
                "organization": update.get("organization") or state.get("organization"),
                "project": update.get("project") or state.get("project"),
                "status": update.get("status") or state.get("status"),
                "phase": phase_name,
                "duration_ms": duration_ms,
                "graph_name": "dod",
                "assistant_name": "dod",
            },
        )
        return merged

    return run


def _validate_checkpoint_state(state: DodGraphState, context: str) -> dict[str, Any]:
    settings = get_settings()
    return validate_graph_state(
        state,
        context=context,
        warn_bytes=int(settings.DOD_GRAPH_STATE_WARN_BYTES),
        max_bytes=int(settings.DOD_GRAPH_STATE_MAX_BYTES),
    )


def _compact_guard_failure(
    state: DodGraphState,
    phase: str,
    exc: GraphStateValidationError,
    duration_ms: int,
) -> DodGraphState:
    phase_durations = _safe_phase_durations(state.get("phase_durations_ms"))
    phase_durations[phase] = max(0, duration_ms)
    diagnostics = _compact_diagnostics(exc.diagnostics)
    failure: DodGraphState = {
        "run_id": state.get("run_id") if isinstance(state.get("run_id"), str) else None,
        "build_id": state.get("build_id") if isinstance(state.get("build_id"), int) else 0,
        "organization": (
            state.get("organization") if isinstance(state.get("organization"), str) else ""
        ),
        "project": state.get("project") if isinstance(state.get("project"), str) else "",
        "mode": state.get("mode") if isinstance(state.get("mode"), str) else "local",
        "correlation_id": (
            state.get("correlation_id")
            if isinstance(state.get("correlation_id"), str)
            else None
        ),
        "requested_by": None,
        "source": None,
        "metadata": {},
        "confidence_threshold": 0.70,
        "high_risk_confidence_threshold": 0.85,
        "input": {},
        "status": STATUS_FAILED,
        "current_phase": phase,
        "started_at": state.get("started_at")
        if isinstance(state.get("started_at"), str)
        else None,
        "completed_at": None,
        "raw_summary": None,
        "canonical_summary": None,
        "evidence_summary": None,
        "bucket_3_summary": None,
        "validation_summary": None,
        "evidence_quality": None,
        "prompt_strategy": None,
        "risk_tier": None,
        "routing_decisions": [],
        "service_now_payload": None,
        "confidence": None,
        "rule_evaluation_summary": None,
        "artifact_paths": _safe_artifact_paths(state.get("artifact_paths")),
        "phase_durations_ms": phase_durations,
        "warnings": [],
        "errors": [
            {
                "severity": "error",
                "code": exc.code,
                "message": "Graph state could not be persisted safely.",
                "phase": phase,
                "diagnostics": diagnostics,
            }
        ],
    }
    for key in LEGACY_LARGE_STATE_KEYS:
        failure[key] = {} if key in {"run_summary", "routing_decisions_bundle"} else None
    return failure


def _compact_diagnostics(diagnostics: dict[str, Any] | Any) -> dict[str, Any]:
    payload = diagnostics if isinstance(diagnostics, dict) else {}
    return {
        key: payload[key]
        for key in (
            "phase",
            "context",
            "python_type",
            "state_size_bytes",
            "warn_bytes",
            "max_bytes",
            "largest_keys",
            "non_serializable_paths",
            "unexpected_keys",
            "exception_type",
        )
        if key in payload
    }


def _safe_artifact_paths(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item
        for key, item in list(value.items())[:100]
        if isinstance(key, str) and isinstance(item, str)
    }


def _safe_phase_durations(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): int(item)
        for key, item in value.items()
        if isinstance(key, str) and isinstance(item, int | float) and not isinstance(item, bool)
    }


def _log_state_diagnostics(state: DodGraphState, phase: str) -> None:
    diagnostics = graph_state_diagnostics(state, phase=phase)
    logger.info("graph_state_diagnostics=%s", diagnostics)
