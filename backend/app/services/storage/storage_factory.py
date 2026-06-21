"""Storage backend selection for DoD artifacts."""

from __future__ import annotations

from backend.app.services.storage.artifact_store import ArtifactStore
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import Settings, get_settings

LOCAL_JSON_BACKEND = "local_json"
COSMOS_BACKEND = "cosmos"
DEPRECATED_COSMOS_LOCAL_BACKEND = "cosmos_local"
SUPPORTED_STORAGE_BACKENDS = {LOCAL_JSON_BACKEND, COSMOS_BACKEND}


def get_storage_store(settings: Settings | None = None, run_id: str | None = None) -> ArtifactStore:
    """Return the configured artifact store."""

    resolved = settings or get_settings()
    backend = (resolved.DOD_STORAGE_BACKEND or LOCAL_JSON_BACKEND).strip().lower()
    if backend == LOCAL_JSON_BACKEND:
        return LocalJsonStore(resolved)
    if backend in {COSMOS_BACKEND, DEPRECATED_COSMOS_LOCAL_BACKEND}:
        from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore

        return CosmosArtifactStore(resolved, run_id=run_id)
    raise ValueError(
        "Invalid DOD_STORAGE_BACKEND. Expected one of: "
        f"{', '.join(sorted(SUPPORTED_STORAGE_BACKENDS))}."
    )
