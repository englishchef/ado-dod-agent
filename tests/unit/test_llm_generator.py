"""Tests for Phase 5B LLM generator service."""

from __future__ import annotations

import json
from typing import Any

from backend.app.services.llm.azure_foundry_client import LlmClientError
from backend.app.services.llm.generator import (
    generate_all_buckets,
    generate_bucket_1,
    generate_bucket_2,
    generate_bucket_3,
)
from backend.app.utils.config import Settings
from pytest import MonkeyPatch, raises


class DummyClient:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.prompts: list[str] = []

    def invoke_text(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("unexpected repair retry or extra model call")
        return json.dumps(self.responses.pop(0))


def _bucket_1_response() -> dict[str, Any]:
    return {
        "target_fields": ["change_description", "short_change_description", "justification"],
        "change_description": "Pipeline scripts were updated.",
        "short_change_description": "Update pipeline scripts",
        "justification": "Available commit evidence indicates a pipeline update.",
        "evidence_used": ["raw.changes.value[0]"],
        "missing_information": ["PR metadata not available"],
        "model_confidence": 0.72,
        "generation_notes": ["Justification inferred from commit evidence."],
    }


def _bucket_2_response() -> dict[str, Any]:
    return {
        "target_fields": ["testing_performed", "implementation_plan", "validation_plan"],
        "testing_performed": (
            "No automated test results were available in the collected evidence."
        ),
        "implementation_plan": "Use the pipeline stage and artifact evidence to deploy.",
        "validation_plan": "Validate successful stage and task completion after deployment.",
        "evidence_used": ["raw.timeline.records[0]"],
        "missing_information": ["test results missing"],
        "model_confidence": 0.63,
        "generation_notes": ["Testing language is conservative because tests are missing."],
    }


def _bucket_3_response() -> dict[str, Any]:
    return {
        "target_fields": ["backout_plan", "risk_impact_analysis"],
        "backout_plan": "Redeploy the previous known-good artifact if needed.",
        "risk_impact_analysis": "Missing test evidence increases deployment uncertainty.",
        "evidence_used": ["raw.artifacts.value[0]"],
        "missing_information": ["explicit rollback task missing"],
        "model_confidence": 0.58,
        "generation_notes": ["Rollback plan is conservative."],
    }


def _evidence_bundle() -> dict[str, Any]:
    return {
        "build_id": 42,
        "organization": "org",
        "project": "proj",
        "bucket_1": {"commit_evidence": [{"source_ref": "raw.changes.value[0]"}]},
        "bucket_2": {"test_evidence": {"total_tests": 0}},
        "bucket_3": {"rollback_indicators": ["artifact"]},
    }


def test_generate_bucket_1_parses_mocked_json_response() -> None:
    client = DummyClient([_bucket_1_response()])

    output = generate_bucket_1({"commit_evidence": []}, client)  # type: ignore[arg-type]

    assert output.change_description == "Pipeline scripts were updated."
    assert len(client.prompts) == 1


def test_generate_bucket_2_handles_missing_test_evidence_honestly() -> None:
    client = DummyClient([_bucket_2_response()])

    output = generate_bucket_2({"test_evidence": {"total_tests": 0}}, client)  # type: ignore[arg-type]

    assert "No automated test results" in output.testing_performed
    assert output.missing_information == ["test results missing"]


def test_generate_bucket_3_parses_rollback_risk_output() -> None:
    client = DummyClient([_bucket_3_response()])

    output = generate_bucket_3({"rollback_indicators": []}, client)  # type: ignore[arg-type]

    assert "previous known-good" in output.backout_plan


def test_generate_all_buckets_calls_model_exactly_three_times(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.app.services.llm.generator.get_settings",
        lambda: Settings(
            AZURE_OPENAI_DEPLOYMENT="deployment",
            AZURE_OPENAI_API_VERSION="2024-10-21",
            AZURE_OPENAI_AUTH_MODE="entra",
        ),
    )
    client = DummyClient([_bucket_1_response(), _bucket_2_response(), _bucket_3_response()])

    outputs = generate_all_buckets(42, _evidence_bundle(), client, "evidence_bundle.json")  # type: ignore[arg-type]

    assert outputs.bucket_1.change_description
    assert len(client.prompts) == 3


def test_generation_fails_clearly_when_output_does_not_match_schema() -> None:
    client = DummyClient([{"target_fields": [], "model_confidence": 0.5}])

    with raises(LlmClientError, match="schema validation"):
        generate_bucket_1({}, client)  # type: ignore[arg-type]

    assert len(client.prompts) == 1
