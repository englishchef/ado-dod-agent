"""FastAPI entrypoint for ado-dod-agent."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.responses import Response

from backend.app.routers.dod_runs import router as dod_runs_router
from backend.app.routers.health import router as health_router
from backend.app.routers.smoke import router as smoke_router
from backend.app.utils.config import ensure_data_directories, get_settings
from backend.app.utils.constants import API_V1_PREFIX, CORRELATION_ID_HEADER, SERVICE_NAME
from backend.app.utils.logging import (
    clear_correlation_id,
    configure_logging,
    get_logger,
    set_correlation_id,
)

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize runtime resources at startup."""

    ensure_data_directories(settings)
    logger.info(
        "service_startup env=%s host=%s port=%s data_dir=%s",
        settings.APP_ENV,
        settings.APP_HOST,
        settings.APP_PORT,
        settings.DATA_DIR,
    )
    yield
    logger.info("service_shutdown")


app = FastAPI(
    title=SERVICE_NAME,
    version="0.1.0",
    description=(
        "Phase 4 foundation for ADO auth, raw collection, canonical normalization, "
        "and deterministic evidence bucket generation."
    ),
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(dod_runs_router, prefix=f"{API_V1_PREFIX}/runs", tags=["dod-runs"])
app.include_router(smoke_router)


@app.middleware("http")
async def correlation_id_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a correlation id to logs and responses for each request."""

    correlation_id = request.headers.get(CORRELATION_ID_HEADER, str(uuid4()))
    set_correlation_id(correlation_id)
    try:
        response = await call_next(request)
    finally:
        clear_correlation_id()
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    return response
