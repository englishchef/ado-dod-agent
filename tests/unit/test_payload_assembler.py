"""Tests for final ServiceNow payload assembly."""

from __future__ import annotations

from backend.app.services.validation.payload_assembler import assemble_service_now_payload


def _valid_payload_dict() -> dict[str, str]:
    return {
        "change_description": "Change description",
        "short_change_description": "Short change",
        "justification": "Justification",
        "testing_performed": "No automated test results were available in collected evidence.",
        "implementation_plan": "Implementation plan",
        "validation_plan": "Validation plan",
        "backout_plan": "Backout plan",
        "risk_impact_analysis": "Risk analysis",
    }


def test_assembler_combines_bucket_outputs_into_exactly_8_fields() -> None:
    expected = _valid_payload_dict()
    payload = assemble_service_now_payload(
        {
            "bucket_1": {
                "change_description": expected["change_description"],
                "short_change_description": expected["short_change_description"],
                "justification": expected["justification"],
                "evidence_used": ["x"],
            },
            "bucket_2": {
                "testing_performed": expected["testing_performed"],
                "implementation_plan": expected["implementation_plan"],
                "validation_plan": expected["validation_plan"],
            },
            "bucket_3": {
                "backout_plan": expected["backout_plan"],
                "risk_impact_analysis": expected["risk_impact_analysis"],
                "metadata": "excluded",
            },
        }
    )

    assert payload.model_dump() == expected
    assert len(payload.model_dump()) == 8
    assert "evidence_used" not in payload.model_dump()
