"""Storage backend selection for DoD artifacts."""

from __future__ import annotations

from typing import Any

from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import Settings, get_settings

LOCAL_JSON_BACKEND = "local_json"
COSMOS_LOCAL_BACKEND = "cosmos_local"
SUPPORTED_STORAGE_BACKENDS = {LOCAL_JSON_BACKEND, COSMOS_LOCAL_BACKEND}


def get_storage_store(settings: Settings | None = None) -> Any:
    """Return the configured artifact store."""

    resolved = settings or get_settings()
    backend = (resolved.DOD_STORAGE_BACKEND or LOCAL_JSON_BACKEND).strip().lower()
    if backend == LOCAL_JSON_BACKEND:
        return LocalJsonStore(resolved)
    if backend == COSMOS_LOCAL_BACKEND:
        from backend.app.services.storage.cosmos_local_store import CosmosLocalStore

        return CosmosLocalStore(resolved)
    raise ValueError(
        "Invalid DOD_STORAGE_BACKEND. Expected one of: "
        f"{', '.join(sorted(SUPPORTED_STORAGE_BACKENDS))}."
    )
