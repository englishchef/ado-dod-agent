"""Tests for collect_raw_metadata CLI summary formatting."""

from __future__ import annotations

from scripts.collect_raw_metadata import format_result_summary


def test_cli_summary_does_not_emit_raw_payload_or_tokens() -> None:
    """CLI summary should avoid printing full raw JSON and sensitive values."""

    result = {
        "collection_run_id": "dod-raw-1-42",
        "status": "partial",
        "build_id": 42,
        "pipeline_name": "Build Pipeline",
        "branch": "refs/heads/main",
        "build_status": "completed",
        "build_result": "failed",
        "summary": {"change_count": 1},
        "artifact_paths": {"raw_bundle": "data/raw/42/raw_bundle.json"},
        "errors": [{"collector": "quality_context", "message": "permission denied"}],
        "raw": {"Authorization": "Bearer super-secret-token", "build": {"huge": "payload"}},
    }

    rendered = format_result_summary(result)
    assert "raw_bundle_path" in rendered
    assert "super-secret-token" not in rendered
    assert '"huge": "payload"' not in rendered
