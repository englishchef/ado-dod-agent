"""Tests for the local-only Cosmos emulator adapter."""

from __future__ import annotations

from backend.app.services.storage.cosmos_local_store import CosmosLocalStore
from backend.app.utils.config import Settings


def test_cosmos_local_store_imports_without_connecting() -> None:
    store = CosmosLocalStore(
        Settings(
            DOD_STORAGE_BACKEND="cosmos_local",
            COSMOS_LOCAL_KEY="local-test-key",
        )
    )

    assert store.settings.COSMOS_LOCAL_DATABASE == "dod_agent_local"
    assert store.settings.COSMOS_LOCAL_CONTAINER == "dod_runs"
    assert store._container is None


def test_cosmos_local_paths_are_safe_references() -> None:
    store = CosmosLocalStore(
        Settings(
            DOD_STORAGE_BACKEND="cosmos_local",
            COSMOS_LOCAL_KEY="local-test-key",
        )
    )

    assert store.output_path(123, "run_summary.json").startswith("cosmos-local://")
