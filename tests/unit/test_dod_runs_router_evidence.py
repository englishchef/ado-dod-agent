"""Tests for evidence generation endpoint behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from backend.api.main import app
from backend.app.models.canonical import (
    CanonicalDodDocument,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)
from backend.app.models.evidence import (
    ChangeIntentEvidence,
    EvidenceBundle,
    EvidenceGenerationMetadata,
    EvidenceServiceContext,
    ExecutionValidationEvidence,
    RiskFlagsEvidence,
    RollbackRiskEvidence,
    TestEvidenceSummary as TestEvidenceSummaryModel,
)
from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def _canonical_payload(build_id: int) -> dict[str, Any]:
    document = CanonicalDodDocument(
        build_id=build_id,
        organization="org",
        project="proj",
        generated_at=datetime.now(UTC),
        run_context=RunContext(build_id=build_id, pipeline_name="Pipeline"),
        change_context=ChangeContext(),
        execution_context=ExecutionContext(),
        quality_context=QualityContext(),
        risk_context=RiskContext(),
        normalization_metadata=NormalizationMetadata(),
    )
    return document.model_dump(mode="json")


def _evidence_bundle(build_id: int) -> EvidenceBundle:
    service_context = EvidenceServiceContext(build_id=build_id, pipeline_name="Pipeline")
    return EvidenceBundle(
        build_id=build_id,
        organization="org",
        project="proj",
        generated_at=datetime.now(UTC),
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
    )


def test_build_evidence_endpoint_returns_expected_summary(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should return safe summary with output artifact paths."""

    from backend.app.routers import dod_runs as runs_route

    class DummyStore:
        def __init__(self, _: Any) -> None:
            pass

        def load_canonical(self, build_id: int) -> dict[str, Any]:
            return _canonical_payload(build_id)

        def normalized_path(self, build_id: int, filename: str) -> str:
            return f"data/normalized/{build_id}/{filename}"

        def save_evidence_json(self, build_id: int, filename: str, payload: Any) -> str:
            _ = payload
            return f"data/evidence/{build_id}/{filename}"

    def fake_build_bundle(
        canonical: Any,
        source_path: str | None = None,
        max_items_per_section: int = 10,
    ) -> EvidenceBundle:
        _ = (canonical, source_path, max_items_per_section)
        return _evidence_bundle(42)

    def fake_summary(bundle: EvidenceBundle, bucket_paths: dict[str, str]) -> dict[str, Any]:
        _ = bundle
        return {
            "status": "completed",
            "message": "Evidence bucket generation completed.",
            "build_id": 42,
            "pipeline_name": "Pipeline",
            "bucket_1_counts": {"work_items": 0, "commits": 0, "pull_requests": 0},
            "bucket_2_counts": {
                "stages": 0,
                "jobs": 0,
                "tasks": 0,
                "artifacts": 0,
                "test_runs": 0,
                "failed_tests": 0,
            },
            "bucket_3_counts": {"artifacts": 0, "failures_or_warnings": 0, "risk_signals": 0},
            "evidence_gap_counts": {"bucket_1": 0, "bucket_2": 0, "bucket_3": 0},
            "truncation_applied": False,
            "output_paths": bucket_paths,
        }

    monkeypatch.setattr(runs_route, "LocalJsonStore", DummyStore)
    monkeypatch.setattr(runs_route, "build_evidence_bundle", fake_build_bundle)
    monkeypatch.setattr(runs_route, "build_evidence_summary", fake_summary)

    client = TestClient(app)
    response = client.post("/api/v1/runs/build-evidence", json={"build_id": 42})
    assert response.status_code == 200
    payload = response.json()
    assert payload["build_id"] == 42
    assert payload["pipeline_name"] == "Pipeline"
    assert payload["output_paths"]["evidence_bundle_path"].endswith(
        "data/evidence/42/evidence_bundle.json"
    )
