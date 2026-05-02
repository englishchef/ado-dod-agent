"""Run orchestration API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.app.models.inputs import CollectRawInput, GenerateRunInput, NormalizeRawInput
from backend.app.models.outputs import (
    NormalizeRawResponse,
    RawCollectionResult,
    RunGenerationResponse,
)
from backend.app.services.collectors.raw_metadata import collect_raw_metadata
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
            "Phase 3 supports raw metadata collection (/api/v1/runs/collect-raw) and "
            "deterministic normalization (/api/v1/runs/normalize); full generation workflow "
            "is not implemented yet."
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
