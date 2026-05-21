"""Deterministic repair helpers for malformed LLM JSON output."""

from __future__ import annotations

from typing import Any

from backend.app.services.llm.json_parser import JsonParseError, extract_json_object

ALIASES = {
    "risk_and_impact_analysis": "risk_impact_analysis",
    "risk_impact": "risk_impact_analysis",
    "rollback_plan": "backout_plan",
    "backout_strategy": "backout_plan",
    "test_plan": "validation_plan",
    "implementation_steps": "implementation_plan",
    "short_description": "short_change_description",
}


def repair_json_text(text: str) -> dict[str, Any]:
    """Extract one JSON object from raw text without evaluating code."""

    try:
        return extract_json_object(text)
    except JsonParseError:
        raise


def normalize_field_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize common field aliases without changing business content."""

    repaired = dict(payload)
    for alias, canonical in ALIASES.items():
        if alias in repaired and canonical not in repaired:
            repaired[canonical] = repaired.pop(alias)
    return repaired


def repair_llm_output_shape(payload: dict[str, Any]) -> dict[str, Any]:
    """Repair structural fields required by Phase 5B output models."""

    repaired = normalize_field_aliases(payload)
    for key in ("evidence_used", "missing_information", "generation_notes"):
        value = repaired.get(key)
        if value is None:
            repaired[key] = []
        elif not isinstance(value, list):
            repaired[key] = [str(value)]

    if "model_confidence" in repaired:
        repaired["model_confidence"] = _repair_confidence(repaired["model_confidence"])

    return repaired


def _repair_confidence(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        try:
            if stripped.endswith("%"):
                return max(0.0, min(float(stripped[:-1]) / 100, 1.0))
            return float(stripped)
        except ValueError:
            return value
    if isinstance(value, (int, float)) and 1 < float(value) <= 100:
        return max(0.0, min(float(value) / 100, 1.0))
    return value
