"""Health-check endpoint."""

from __future__ import annotations

from typing import Annotated

from backend.app.models.outputs import HealthResponse
from backend.app.utils.config import Settings, get_settings
from backend.app.utils.constants import SERVICE_NAME
from fastapi import APIRouter, Depends

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return service health and runtime metadata."""

    return HealthResponse(status="ok", service=SERVICE_NAME, environment=settings.APP_ENV)

