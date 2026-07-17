"""State contract for the LangGraph deployment adapter."""

from __future__ import annotations

from typing import Any, TypedDict

from backend.app.models.dod_contracts import normalize_dod_run_input
from backend.app.utils.state_serialization import to_json_safe


class DoDGraphState(TypedDict, total=False):
    """Structured input and output state for the deployed DoD assistant."""

    organization: str
    project: str
    build_id: int
    mode: str
    correlation_id: str | None
    requested_by: str | None
    source: str | None
    metadata: dict[str, Any]

    run_id: str | None
    status: str | None
    current_phase: str | None

    service_now_payload: dict[str, Any] | None
    confidence: dict[str, Any] | None
    rule_evaluation_summary: dict[str, Any] | None
    artifact_paths: dict[str, str]
    warnings: list[dict[str, Any]]
    errors: list[dict[str, Any]]

    result: dict[str, Any] | None


def normalize_dod_input(state: DoDGraphState) -> DoDGraphState:
    """Validate and normalize the structured DoD graph input."""

    contract = normalize_dod_run_input(state)
    metadata = to_json_safe(contract.metadata, context="metadata")
    normalized: DoDGraphState = {
        "organization": contract.organization,
        "project": contract.project,
        "build_id": contract.build_id,
        "mode": contract.mode,
        "correlation_id": contract.correlation_id,
        "requested_by": contract.requested_by,
        "source": contract.source,
        "metadata": metadata,
        "run_id": state.get("run_id"),
        "status": state.get("status"),
        "current_phase": state.get("current_phase") or "input_normalization",
        "service_now_payload": None,
        "confidence": None,
        "rule_evaluation_summary": None,
        "artifact_paths": dict(state.get("artifact_paths") or {}),
        "warnings": list(state.get("warnings") or []),
        "errors": list(state.get("errors") or []),
        "result": None,
    }
    return normalized
