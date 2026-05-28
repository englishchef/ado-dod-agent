"""Helpers for recording routing decisions in graph state."""

from __future__ import annotations

from typing import Any

from backend.app.models.routing import RoutingDecision


def make_decision(
    step: str,
    decision: str,
    reason: str,
    severity: str = "info",
    metadata: dict[str, Any] | None = None,
) -> RoutingDecision:
    """Create a structured routing decision."""

    return RoutingDecision(
        step=step,
        decision=decision,
        reason=reason,
        severity=severity,  # type: ignore[arg-type]
        metadata=dict(metadata or {}),
    )


def append_decision(state: dict[str, Any], decision: RoutingDecision) -> dict[str, Any]:
    """Return a partial state update with a routing decision appended."""

    decisions = list(state.get("routing_decisions") or [])
    decisions.append(decision.model_dump(mode="json"))
    return {"routing_decisions": decisions}
