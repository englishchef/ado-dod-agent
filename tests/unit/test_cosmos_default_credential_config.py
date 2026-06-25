"""Tests for Cosmos default credential configuration."""

from __future__ import annotations

from typing import Any

import pytest
from backend.app.services.storage import cosmos_artifact_store
from backend.app.services.storage.cosmos_artifact_store import _required_cosmos_config
from backend.app.utils.config import Settings


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "DOD_STORAGE_BACKEND": "cosmos",
        "COSMOS_AUTH_MODE": "default_credential",
        "COSMOS_ENDPOINT": "https://example.documents.azure.com:443/",
        "COSMOS_DATABASE": "dod_agent",
        "COSMOS_CONTAINER": "dod_runs",
        "COSMOS_KEY": None,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_cosmos_default_credential_does_not_require_cosmos_key(monkeypatch: Any) -> None:
    credential = object()
    monkeypatch.setattr(
        cosmos_artifact_store,
        "get_azure_credential",
        lambda: credential,
    )

    _, resolved_credential, _, _ = _required_cosmos_config(_settings())

    assert resolved_credential is credential


def test_cosmos_key_mode_requires_cosmos_key() -> None:
    with pytest.raises(ValueError, match="COSMOS_KEY"):
        _required_cosmos_config(_settings(COSMOS_AUTH_MODE="key", COSMOS_KEY=None))


def test_cosmos_emulator_key_mode_requires_cosmos_key() -> None:
    with pytest.raises(ValueError, match="COSMOS_KEY"):
        _required_cosmos_config(_settings(COSMOS_AUTH_MODE="emulator_key", COSMOS_KEY=None))
