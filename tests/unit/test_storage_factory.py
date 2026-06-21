"""Tests for artifact storage backend selection."""

from __future__ import annotations

from pathlib import Path

import pytest
from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.services.storage.storage_factory import get_storage_store
from backend.app.utils.config import Settings


def test_local_json_backend_selects_local_store(tmp_path: Path) -> None:
    store = get_storage_store(Settings(DOD_STORAGE_BACKEND="local_json", DATA_DIR=tmp_path))

    assert isinstance(store, LocalJsonStore)


def test_cosmos_backend_selects_cosmos_artifact_store() -> None:
    store = get_storage_store(
        Settings(
            DOD_STORAGE_BACKEND="cosmos",
            COSMOS_AUTH_MODE="emulator_key",
            COSMOS_ENDPOINT="https://localhost:8081",
            COSMOS_DATABASE="dod_agent_local",
            COSMOS_CONTAINER="dod_runs",
            COSMOS_KEY="local-test-key",
        ),
        run_id="run-1",
    )

    assert isinstance(store, CosmosArtifactStore)
    assert store.default_run_id == "run-1"


def test_invalid_backend_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Invalid DOD_STORAGE_BACKEND"):
        get_storage_store(Settings(DOD_STORAGE_BACKEND="invalid"))
