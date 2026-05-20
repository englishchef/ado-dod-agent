"""Tests for Phase 5B generated output models."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.llm_outputs import (
    Bucket1GeneratedOutput,
    Bucket2GeneratedOutput,
    Bucket3GeneratedOutput,
    CombinedLlmOutputs,
    LlmModelMetadata,
)
from pydantic import ValidationError
from pytest import raises


def _bucket_1(confidence: float = 0.8) -> Bucket1GeneratedOutput:
    return Bucket1GeneratedOutput(
        change_description="Change updates the pipeline scripts.",
        short_change_description="Update pipeline scripts",
        justification="Commit evidence indicates a pipeline reliability update.",
        evidence_used=["raw.changes.value[0]"],
        missing_information=["PR metadata not available"],
        model_confidence=confidence,
        generation_notes=[],
    )


def _bucket_2(confidence: float = 0.7) -> Bucket2GeneratedOutput:
    return Bucket2GeneratedOutput(
        testing_performed="No automated test results were available in evidence.",
        implementation_plan="Deploy the generated artifact through the pipeline stages.",
        validation_plan="Validate using available stage and task success signals.",
        evidence_used=["raw.timeline.records[0]"],
        missing_information=["test results missing"],
        model_confidence=confidence,
        generation_notes=[],
    )


def _bucket_3(confidence: float = 0.6) -> Bucket3GeneratedOutput:
    return Bucket3GeneratedOutput(
        backout_plan="Redeploy the previous known-good artifact if rollback is required.",
        risk_impact_analysis="Missing test evidence increases uncertainty.",
        evidence_used=["raw.artifacts.value[0]"],
        missing_information=["explicit rollback task missing"],
        model_confidence=confidence,
        generation_notes=[],
    )


def test_bucket_1_generated_output_validates() -> None:
    output = _bucket_1()

    assert output.target_fields == [
        "change_description",
        "short_change_description",
        "justification",
    ]


def test_bucket_2_generated_output_validates() -> None:
    output = _bucket_2()

    assert "testing_performed" in output.target_fields


def test_bucket_3_generated_output_validates() -> None:
    output = _bucket_3()

    assert "risk_impact_analysis" in output.target_fields


def test_model_confidence_outside_range_fails() -> None:
    with raises(ValidationError):
        _bucket_1(confidence=1.5)


def test_bucket_1_long_short_description_adds_generation_note() -> None:
    output = Bucket1GeneratedOutput(
        change_description="Change updates the pipeline scripts.",
        short_change_description="x" * 170,
        justification="Commit evidence indicates a pipeline reliability update.",
        evidence_used=[],
        missing_information=[],
        model_confidence=0.8,
        generation_notes=[],
    )

    assert any("short_change_description" in note for note in output.generation_notes)


def test_combined_llm_outputs_serializes() -> None:
    combined = CombinedLlmOutputs(
        build_id=123,
        organization="org",
        project="proj",
        generated_at=datetime.now(UTC),
        source_evidence_bundle_path="data/evidence/123/evidence_bundle.json",
        model_metadata=LlmModelMetadata(
            provider="azure_openai",
            deployment="deployment",
            api_version="2024-10-21",
            auth_mode="entra",
            prompt_versions={"bucket_1": "1.0", "bucket_2": "1.0", "bucket_3": "1.0"},
        ),
        bucket_1=_bucket_1(),
        bucket_2=_bucket_2(),
        bucket_3=_bucket_3(),
    )

    payload = combined.model_dump(mode="json")
    assert payload["build_id"] == 123
    assert payload["bucket_1"]["change_description"]
