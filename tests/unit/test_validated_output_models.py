"""Tests for Phase 6 validated output models."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.validated_outputs import (
    ConfidenceScore,
    ServiceNowPayload,
    ValidatedDodOutput,
    ValidationIssue,
)
from pydantic import ValidationError
from pytest import raises


def valid_payload() -> ServiceNowPayload:
    return ServiceNowPayload(
        change_description="Change description",
        short_change_description="Short change",
        justification="Justification",
        testing_performed="No automated test results were available in collected evidence.",
        implementation_plan="Implementation plan",
        validation_plan="Validation plan",
        backout_plan="Backout plan",
        risk_impact_analysis="Risk analysis",
    )


def test_service_now_payload_validates_all_8_fields() -> None:
    payload = valid_payload()

    assert len(payload.model_dump()) == 8


def test_service_now_payload_rejects_empty_field() -> None:
    with raises(ValidationError):
        ServiceNowPayload.model_validate({**valid_payload().model_dump(), "justification": ""})


def test_service_now_payload_rejects_placeholder() -> None:
    with raises(ValidationError):
        ServiceNowPayload.model_validate({**valid_payload().model_dump(), "justification": "TBD"})


def test_confidence_score_rejects_out_of_range() -> None:
    with raises(ValidationError):
        ConfidenceScore(
            overall=1.2,
            bucket_1=0.5,
            bucket_2=0.5,
            bucket_3=0.5,
            rationale={},
        )


def test_validated_dod_output_serializes() -> None:
    confidence = ConfidenceScore(
        overall=0.7,
        bucket_1=0.8,
        bucket_2=0.7,
        bucket_3=0.6,
        rationale={"overall": ["average"]},
    )
    output = ValidatedDodOutput(
        build_id=1,
        generated_at=datetime.now(UTC),
        is_valid=True,
        service_now_payload=valid_payload(),
        bucket_validation_results=[],
        confidence=confidence,
        validation_issues=[ValidationIssue(severity="info", code="i", message="m")],
    )

    assert output.model_dump(mode="json")["service_now_payload"]["justification"]
