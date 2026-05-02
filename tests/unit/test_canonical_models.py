"""Tests for canonical model serialization."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.canonical import (
    CanonicalDodDocument,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)


def test_canonical_document_serializes_to_json() -> None:
    """Canonical model should serialize cleanly to JSON."""

    document = CanonicalDodDocument(
        build_id=42,
        organization="org",
        project="project",
        generated_at=datetime(2026, 5, 2, tzinfo=UTC),
        source_raw_bundle_path="data/raw/42/raw_bundle.json",
        run_context=RunContext(build_id=42),
        change_context=ChangeContext(),
        execution_context=ExecutionContext(),
        quality_context=QualityContext(),
        risk_context=RiskContext(),
        normalization_metadata=NormalizationMetadata(),
    )

    payload = document.model_dump(mode="json")
    assert payload["build_id"] == 42
    assert payload["schema_version"] == "1.0"
    assert "run_context" in payload
