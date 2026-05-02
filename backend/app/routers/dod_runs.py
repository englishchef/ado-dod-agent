"""Run orchestration API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from backend.app.models.canonical import CanonicalDodDocument
from backend.app.models.inputs import (
    BuildEvidenceInput,
    CollectRawInput,
    GenerateRunInput,
    NormalizeRawInput,
)
from backend.app.models.outputs import (
    BuildEvidenceResponse,
    NormalizeRawResponse,
    RawCollectionResult,
    RunGenerationResponse,
)
from backend.app.services.collectors.raw_metadata import collect_raw_metadata
from backend.app.services.evidence.builder import build_evidence_bundle, build_evidence_summary
from backend.app.services.normalizers.canonical import (
    build_canonical_summary,
    normalize_raw_bundle,
)
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import get_settings

router = APIRouter()


@router.post(
    "/generate",
    response_model=RunGenerationResponse,
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)
async def generate_run(_: GenerateRunInput) -> RunGenerationResponse:
    """Placeholder endpoint for future pipeline summary generation."""

    return RunGenerationResponse(
        status="not_implemented",
        message=(
            "Phase 4 supports raw metadata collection (/api/v1/runs/collect-raw), "
            "deterministic normalization (/api/v1/runs/normalize), and deterministic "
            "evidence bucket generation (/api/v1/runs/build-evidence); full generation "
            "workflow is not implemented yet."
        ),
    )


@router.post("/collect-raw", response_model=RawCollectionResult)
async def collect_raw(request: CollectRawInput) -> RawCollectionResult:
    """Collect raw build metadata and persist local artifacts."""

    result = await collect_raw_metadata(request)
    if result.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Raw metadata collection failed at mandatory build retrieval stage.",
                "collection_run_id": result.collection_run_id,
                "build_id": result.build_id,
                "errors": [error.model_dump() for error in result.errors],
            },
        )
    return result


@router.post("/normalize", response_model=NormalizeRawResponse)
async def normalize_raw(request: NormalizeRawInput) -> NormalizeRawResponse:
    """Normalize previously collected raw metadata into canonical structure."""

    settings = get_settings()
    store = LocalJsonStore(settings)

    source_path: str | None = request.raw_bundle_path
    try:
        if request.raw_bundle_path:
            payload_text = Path(request.raw_bundle_path).read_text(encoding="utf-8")
            raw_bundle: dict[str, Any] = json.loads(payload_text)
        else:
            raw_bundle = store.load_raw_bundle(request.build_id)
            source_path = store.raw_path(request.build_id, "raw_bundle.json")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raw bundle not found for build_id={request.build_id}.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Raw bundle is not valid JSON for build_id={request.build_id}.",
        ) from exc

    raw_bundle["build_id"] = request.build_id
    if request.organization:
        raw_bundle["organization"] = request.organization
    if request.project:
        raw_bundle["project"] = request.project

    document = normalize_raw_bundle(raw_bundle=raw_bundle, source_path=source_path)
    canonical_path = store.save_normalized_json(
        build_id=request.build_id,
        filename="canonical.json",
        payload=document.model_dump(mode="json"),
    )

    summary = build_canonical_summary(document, canonical_path)
    return NormalizeRawResponse.model_validate(summary)


@router.post("/build-evidence", response_model=BuildEvidenceResponse)
async def build_evidence(request: BuildEvidenceInput) -> BuildEvidenceResponse:
    """Build deterministic evidence buckets from canonical normalized metadata."""

    settings = get_settings()
    store = LocalJsonStore(settings)

    source_path: str | None = request.canonical_path
    try:
        if request.canonical_path:
            payload_text = Path(request.canonical_path).read_text(encoding="utf-8")
            canonical_payload: dict[str, Any] = json.loads(payload_text)
        else:
            canonical_payload = store.load_canonical(request.build_id)
            source_path = store.normalized_path(request.build_id, "canonical.json")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canonical document not found for build_id={request.build_id}.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Canonical document is not valid JSON for build_id={request.build_id}.",
        ) from exc

    canonical_payload["build_id"] = request.build_id
    try:
        canonical_document = CanonicalDodDocument.model_validate(canonical_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Canonical document has invalid schema for build_id={request.build_id}.",
        ) from exc
    evidence_bundle = build_evidence_bundle(
        canonical=canonical_document,
        source_path=source_path,
        max_items_per_section=request.max_items_per_section,
    )

    bucket_1_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="bucket_1_change_intent.json",
        payload=evidence_bundle.bucket_1.model_dump(mode="json"),
    )
    bucket_2_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="bucket_2_execution_validation.json",
        payload=evidence_bundle.bucket_2.model_dump(mode="json"),
    )
    bucket_3_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="bucket_3_rollback_risk.json",
        payload=evidence_bundle.bucket_3.model_dump(mode="json"),
    )
    bundle_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="evidence_bundle.json",
        payload=evidence_bundle.model_dump(mode="json"),
    )
    summary = build_evidence_summary(
        bundle=evidence_bundle,
        bucket_paths={
            "bucket_1_change_intent_path": bucket_1_path,
            "bucket_2_execution_validation_path": bucket_2_path,
            "bucket_3_rollback_risk_path": bucket_3_path,
            "evidence_bundle_path": bundle_path,
        },
    )
    return BuildEvidenceResponse.model_validate(summary)
