"""Phase 7B LangGraph workflow assembly."""

from __future__ import annotations

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

Route = Literal["failed", "continue"]


def build_dod_workflow() -> Any:
    """Build the Phase 7B advanced-routing DoD orchestration graph."""

    graph = StateGraph(DodGraphState)
    graph.add_node("validate_input", validate_input_node)
    graph.add_node("collect_raw_metadata", collect_raw_metadata_node)
    graph.add_node("normalize_canonical", normalize_canonical_node)
    graph.add_node("build_evidence_buckets", build_evidence_buckets_node)
    graph.add_node("assess_evidence_quality", assess_evidence_quality_node)
    graph.add_node("assess_risk_tier", assess_risk_tier_node)
    graph.add_node("select_prompt_strategy", select_prompt_strategy_node)
    graph.add_node("generate_llm_outputs", generate_llm_outputs_node)
    graph.add_node("validate_outputs", validate_outputs_node)
    graph.add_node("evaluate_rules", evaluate_rules_node)
    graph.add_node("assemble_run_result", assemble_run_result_node)
    graph.add_node("persist_routing_decisions", persist_routing_decisions_node)
    graph.add_node("persist_run_summary", persist_run_summary_node)

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
