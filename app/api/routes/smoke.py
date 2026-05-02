"""Smoke validation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.ado_token_provider import AzureDevOpsTokenProvider
from app.core.config import Settings, get_settings
from app.core.constants import API_V1_PREFIX
from app.core.logging import get_logger
from app.models.outputs import SmokeAuthResponse

logger = get_logger(__name__)

router = APIRouter(prefix=f"{API_V1_PREFIX}/smoke", tags=["smoke"])


@router.get("/ado-auth", response_model=SmokeAuthResponse)
async def smoke_ado_auth(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SmokeAuthResponse:
    """Perform a minimal Azure DevOps Entra auth smoke check."""

    if not settings.ADO_ORGANIZATION or not settings.ADO_PROJECT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ADO_ORGANIZATION and ADO_PROJECT must be configured for smoke auth.",
        )

    token_provider = AzureDevOpsTokenProvider(settings=settings)

    try:
        auth_headers = await token_provider.get_auth_headers()
    except Exception as exc:
        logger.warning("ado_auth_smoke_failed error=%s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure DevOps auth smoke check failed. Verify Entra auth and ADO access.",
        ) from exc

    authentication_succeeded = auth_headers.get("Authorization", "").startswith("Bearer ")
    if not authentication_succeeded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure DevOps auth smoke check did not return a bearer token.",
        )

    return SmokeAuthResponse(
        status="ok",
        message="Azure DevOps auth smoke check succeeded.",
        authentication_succeeded=True,
        organization=settings.ADO_ORGANIZATION,
        project=settings.ADO_PROJECT,
    )
