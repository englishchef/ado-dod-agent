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


def make_graph_dod() -> Any:
    """Compile the enterprise LangGraph deployment graph for the DoD assistant."""

    graph = StateGraph(DoDGraphState)
    graph.add_node("run_dod", _run_dod_node)
    graph.add_edge(START, "run_dod")
    graph.add_edge("run_dod", END)
    return graph.compile()


def _run_dod_node(state: DoDGraphState) -> DoDGraphState:
    normalized = normalize_dod_input(state)
    contract_input = normalize_dod_run_input(normalized)
    request = contract_input.model_dump(mode="json")
    output = serialize_dod_run_output(run_dod_agent(request), fallback_input=contract_input)
    trace_event(
        "dod graph output serialization",
        safe_trace_context(
            input_data=request,
            result=output.model_dump(mode="json"),
            storage_backend=None,
        ),
    )

    return cast(DoDGraphState, {
        **normalized,
        **output.model_dump(mode="json"),
    })
