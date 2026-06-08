"""Tests for deterministic ServiceNow field formatting."""

from __future__ import annotations

from backend.app.services.formatting.servicenow_formatter import (
    clean_servicenow_field_text,
    format_service_now_payload,
    normalize_servicenow_whitespace,
    remove_markdown_artifacts,
)


def test_removes_bracketed_raw_reference() -> None:
    assert clean_servicenow_field_text("Deploy API [raw.changes.value[3]]") == "Deploy API"


def test_removes_raw_reference_path() -> None:
    assert clean_servicenow_field_text("Deploy raw.changes.value[3] API") == "Deploy API"


def test_removes_canonical_reference_path() -> None:
    assert (
        clean_servicenow_field_text("Update canonical.change_context.work_items[0] service")
        == "Update service"
    )


def test_removes_evidence_reference_path() -> None:
    assert (
        clean_servicenow_field_text("Validated evidence.bucket_1.work_item_evidence[0] change")
        == "Validated change"
    )


def test_removes_source_ref_leakage() -> None:
    assert clean_servicenow_field_text("source_ref confirms deployment") == "confirms deployment"


def test_removes_markdown_fences() -> None:
    assert remove_markdown_artifacts("```json\nDeployment complete\n```").strip() == (
        "Deployment complete"
    )


def test_normalizes_whitespace() -> None:
    assert normalize_servicenow_whitespace(" Deploy   service \n\n\n Validate   health ") == (
        "Deploy service\n\nValidate health"
    )


def test_preserves_numbered_validation_plan() -> None:
    text = clean_servicenow_field_text("1. Validate API health\n2. Review logs")

    assert text == "1. Validate API health\n2. Review logs"


def test_preserves_business_text() -> None:
    text = clean_servicenow_field_text(
        "Implementation plan: Deploy the approved package through the release pipeline."
    )

    assert text == "Deploy the approved package through the release pipeline."


def test_format_service_now_payload_returns_exactly_8_clean_fields() -> None:
    payload = format_service_now_payload(
        {
            "change_description": "Change [raw.changes.value[3]]",
            "short_change_description": "Short",
            "justification": "Justification",
            "testing_performed": "Testing",
            "implementation_plan": "Implementation",
            "validation_plan": "1. Validate API\n2. Review logs",
            "backout_plan": "Backout",
            "risk_impact_analysis": "Risk",
            "extra": "excluded",
        }
    ).model_dump()

    assert len(payload) == 8
    assert payload["change_description"] == "Change"
    assert "extra" not in payload
