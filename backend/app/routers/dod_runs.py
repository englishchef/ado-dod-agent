"""Run orchestration API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.models.inputs import CollectRawInput, GenerateRunInput
from backend.app.models.outputs import RawCollectionResult, RunGenerationResponse
from backend.app.services.collectors.raw_metadata import collect_raw_metadata

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
            "Phase 2 supports raw metadata collection via /api/v1/runs/collect-raw and "
            "scripts/collect_raw_metadata.py; full generation workflow is not implemented yet."
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
