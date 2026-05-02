"""Health-check endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.constants import SERVICE_NAME
from app.models.outputs import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return service health and runtime metadata."""

    return HealthResponse(status="ok", service=SERVICE_NAME, environment=settings.APP_ENV)
