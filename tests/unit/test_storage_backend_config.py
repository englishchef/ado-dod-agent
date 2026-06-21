"""Tests for artifact storage backend selection."""

from __future__ import annotations

from pathlib import Path

import pytest
from backend.app.services.storage.cosmos_local_store import CosmosLocalStore
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.services.storage.storage_factory import get_storage_store
from backend.app.utils.config import Settings


def test_local_json_backend_selects_local_store(tmp_path: Path) -> None:
    store = get_storage_store(Settings(DOD_STORAGE_BACKEND="local_json", DATA_DIR=tmp_path))

    assert isinstance(store, LocalJsonStore)


def test_cosmos_local_backend_selects_cosmos_local_store() -> None:
    store = get_storage_store(
        Settings(
            DOD_STORAGE_BACKEND="cosmos_local",
            COSMOS_LOCAL_KEY="local-test-key",
        )
    )

    assert isinstance(store, CosmosLocalStore)


def test_invalid_backend_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Invalid DOD_STORAGE_BACKEND"):
        get_storage_store(Settings(DOD_STORAGE_BACKEND="cosmos"))
