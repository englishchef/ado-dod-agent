"""Tests for evidence model serialization."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.evidence import (
    ChangeIntentEvidence,
    EvidenceBundle,
    EvidenceGenerationMetadata,
    EvidenceServiceContext,
    EvidenceSourceRef,
    ExecutionValidationEvidence,
    RiskFlagsEvidence,
    RollbackRiskEvidence,
)
from backend.app.models.evidence import (
    TestEvidenceSummary as TestEvidenceSummaryModel,
)


def test_evidence_bundle_serializes_to_json() -> None:
    """Evidence models should serialize cleanly to JSON."""

    service_context = EvidenceServiceContext(build_id=77, pipeline_name="Pipeline")
    bundle = EvidenceBundle(
        build_id=77,
        organization="org",
        project="proj",
        generated_at=datetime(2026, 5, 2, tzinfo=UTC),
        source_canonical_path="data/normalized/77/canonical.json",
        bucket_1=ChangeIntentEvidence(
            target_fields=["change_description"],
            service_context=service_context,
        ),
        bucket_2=ExecutionValidationEvidence(
            target_fields=["testing_performed"],
            service_context=service_context,
            test_evidence=TestEvidenceSummaryModel(),
        ),
        bucket_3=RollbackRiskEvidence(
            target_fields=["backout_plan"],
            service_context=service_context,
            risk_flags=RiskFlagsEvidence(),
        ),
        generation_metadata=EvidenceGenerationMetadata(generated_sections=["bucket_1"]),
        source_ref_map={
            "work_item:77": EvidenceSourceRef(
                friendly_ref="work_item:77",
                original_ref="raw.work_items.value[0]",
                source_type="work_item",
                display_name="Pipeline change",
            )
        },
    )

    payload = bundle.model_dump(mode="json")
    assert payload["schema_version"] == "1.0"
    assert payload["build_id"] == 77
    assert "bucket_1" in payload
    assert payload["source_ref_map"]["work_item:77"]["original_ref"] == (
        "raw.work_items.value[0]"
    )
