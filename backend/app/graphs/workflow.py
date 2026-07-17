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
from backend.app.graphs.state import STATUS_FAILED, DodGraphState
from backend.app.services.observability.langsmith_tracing import trace_event

Route = Literal["failed", "continue"]
NodeFunc = Callable[[DodGraphState], DodGraphState]


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

    initial_state: DodGraphState = {
        "input": dict(input_data),
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
        started = perf_counter()
        update = node(state)
        duration_ms = int((perf_counter() - started) * 1000)
        phase_durations = dict(state.get("phase_durations_ms") or {})
        phase_durations[phase_name] = duration_ms
        merged: DodGraphState = {**update, "phase_durations_ms": phase_durations}
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
