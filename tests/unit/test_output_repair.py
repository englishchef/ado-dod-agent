"""Tests for deterministic Phase 6 output repair."""

from __future__ import annotations

from backend.app.services.llm.json_parser import JsonParseError
from backend.app.services.validation.output_repair import (
    normalize_field_aliases,
    repair_json_text,
    repair_llm_output_shape,
)
from pytest import raises


def test_repair_json_text_parses_markdown_fenced_json() -> None:
    assert repair_json_text('```json\n{"status":"ok"}\n```') == {"status": "ok"}


def test_repair_json_text_extracts_json_from_extra_text() -> None:
    assert repair_json_text('prefix {"status":"ok"} suffix') == {"status": "ok"}


def test_normalize_alias_rollback_plan_to_backout_plan() -> None:
    assert normalize_field_aliases({"rollback_plan": "rollback"})["backout_plan"] == "rollback"


def test_normalize_alias_risk_and_impact_analysis() -> None:
    payload = normalize_field_aliases({"risk_and_impact_analysis": "risk"})

    assert payload["risk_impact_analysis"] == "risk"


def test_repair_llm_output_shape_fills_required_arrays() -> None:
    payload = repair_llm_output_shape({"model_confidence": "85%"})

    assert payload["evidence_used"] == []
    assert payload["missing_information"] == []
    assert payload["generation_notes"] == []
    assert payload["model_confidence"] == 0.85


def test_repair_json_text_rejects_unrecoverable_json() -> None:
    with raises(JsonParseError):
        repair_json_text("not-json")
