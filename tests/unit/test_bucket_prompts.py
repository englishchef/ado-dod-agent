"""Tests for Phase 5B bucket prompt builders."""

from __future__ import annotations

from backend.app.prompts import (
    bucket_1_change_intent,
    bucket_2_execution_validation,
    bucket_3_rollback_risk,
)


def test_bucket_1_prompt_includes_all_target_field_names() -> None:
    prompt = bucket_1_change_intent.build_prompt({"evidence_references": ["ref"]})

    assert "change_description" in prompt
    assert "short_change_description" in prompt
    assert "justification" in prompt
    assert "Return valid JSON only" in prompt


def test_bucket_2_prompt_includes_missing_test_and_no_hallucination_instruction() -> None:
    prompt = bucket_2_execution_validation.build_prompt({"test_evidence": {}})

    assert "If no test results exist" in prompt
    assert "Do not invent test counts" in prompt
    assert "Return valid JSON only" in prompt


def test_bucket_3_prompt_includes_rollback_not_tested_and_no_hallucination_instruction() -> None:
    prompt = bucket_3_rollback_risk.build_prompt({"rollback_indicators": []})

    assert "Do not claim rollback has been tested unless evidence proves it" in prompt
    assert "Do not invent facts" in prompt
    assert "Return valid JSON only" in prompt
