"""Health-check endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from backend.app.models.api import ReadyResponse
from backend.app.models.outputs import HealthResponse
from backend.app.utils.config import Settings, get_settings
from backend.app.utils.constants import SERVICE_NAME

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return service health and runtime metadata."""

    return HealthResponse(status="ok", service=SERVICE_NAME, environment=settings.APP_ENV)


@router.get("/ready", response_model=ReadyResponse)
def ready(settings: Annotated[Settings, Depends(get_settings)]) -> ReadyResponse | JSONResponse:
    """Return readiness without making live external calls."""

    required_config = {
        "ADO_ORGANIZATION": settings.ADO_ORGANIZATION,
        "ADO_PROJECT": settings.ADO_PROJECT,
        "ADO_API_VERSION": settings.ADO_API_VERSION,
        "AZURE_OPENAI_ENDPOINT": settings.AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_DEPLOYMENT": settings.AZURE_OPENAI_DEPLOYMENT,
        "AZURE_OPENAI_API_VERSION": settings.AZURE_OPENAI_API_VERSION,
        "AZURE_OPENAI_AUTH_MODE": settings.AZURE_OPENAI_AUTH_MODE,
        "DATA_DIR": settings.DATA_DIR,
    }
    configured = [name for name, value in required_config.items() if _is_configured(value)]
    missing = [name for name, value in required_config.items() if not _is_configured(value)]
    payload = ReadyResponse(
        status="ready" if not missing else "not_ready",
        missing_config=missing,
        configured=configured,
    )
    if missing:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(mode="json"),
        )
    return payload


def _is_configured(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True

