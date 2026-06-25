"""Tests for DoD observability redaction helpers."""

from __future__ import annotations

from backend.app.services.observability.redaction import (
    MAX_STRING_LENGTH,
    REDACTED,
    redact_dict,
    safe_run_summary_for_trace,
    safe_trace_metadata,
)


def test_redaction_removes_secret_values_without_partial_exposure() -> None:
    payload = {
        "authorization": "Bearer abc123",
        "COSMOS_KEY": "cosmos-secret",
        "nested": {
            "password": "p@ssw0rd",
            "safe": "visible",
        },
    }

    redacted = redact_dict(payload)

    assert redacted["authorization"] == REDACTED
    assert redacted["COSMOS_KEY"] == REDACTED
    assert redacted["nested"]["password"] == REDACTED
    assert redacted["nested"]["safe"] == "visible"
    assert "abc123" not in str(redacted)
    assert "cosmos-secret" not in str(redacted)
    assert "p@ssw0rd" not in str(redacted)


def test_redaction_handles_nested_lists_and_large_strings() -> None:
    large = "x" * (MAX_STRING_LENGTH + 50)
    payload = {"items": [{"api_key": "secret-key"}, {"note": large}]}

    redacted = redact_dict(payload)

    assert redacted["items"][0]["api_key"] == REDACTED
    assert redacted["items"][1]["note"].endswith("...[TRUNCATED]")
    assert len(redacted["items"][1]["note"]) < len(large)


def test_safe_trace_metadata_drops_raw_payloads_and_full_generated_content() -> None:
    metadata = safe_trace_metadata(
        {
            "run_id": "run-1",
            "build_id": 123,
            "raw_ado_payload": {"secret": "value"},
            "service_now_payload": {"change_description": "full generated field"},
            "prompt": "full prompt",
        }
    )

    assert metadata == {"run_id": "run-1", "build_id": 123}
    assert "full generated field" not in str(metadata)
    assert "full prompt" not in str(metadata)


def test_safe_run_summary_for_trace_uses_counts_and_scores_only() -> None:
    summary = safe_run_summary_for_trace(
        {
            "run_id": "run-1",
            "build_id": 123,
            "status": "completed",
            "service_now_payload": {"change_description": "full generated field"},
            "confidence": {"overall": 0.91},
            "artifact_paths": {"run_summary": "summary.json"},
            "rule_evaluation": {
                "summary": {
                    "recommended_status": "completed",
                    "highest_severity": "info",
                },
                "test_completeness_score": {"score": 0.8},
            },
        }
    )

    assert summary["artifact_count"] == 1
    assert summary["final_confidence"] == 0.91
    assert summary["rule_recommended_status"] == "completed"
    assert "full generated field" not in str(summary)
