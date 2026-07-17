"""State contract for the LangGraph deployment adapter."""

from __future__ import annotations

from typing import Any, TypedDict

from backend.app.models.dod_contracts import normalize_dod_run_input


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
    normalized: DoDGraphState = {
        **state,
        "organization": contract.organization,
        "project": contract.project,
        "build_id": contract.build_id,
        "mode": contract.mode,
        "correlation_id": contract.correlation_id,
        "requested_by": contract.requested_by,
        "source": contract.source,
        "metadata": dict(contract.metadata),
        "artifact_paths": dict(state.get("artifact_paths") or {}),
        "warnings": list(state.get("warnings") or []),
        "errors": list(state.get("errors") or []),
    }
    return normalized
