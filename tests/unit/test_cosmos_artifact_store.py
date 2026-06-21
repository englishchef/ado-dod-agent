"""Tests for the official Cosmos artifact store without an emulator."""

from __future__ import annotations

from typing import Any

import pytest
from backend.app.services.storage.cosmos_artifact_store import (
    COSMOS_PARTITION_KEY,
    CosmosArtifactStore,
    _required_cosmos_config,
)
from backend.app.utils.config import Settings


class FakeContainer:
    def __init__(self) -> None:
        self.documents: dict[tuple[str, str], dict[str, Any]] = {}
        self.upserted: dict[str, Any] | None = None

    def read_item(self, item: str, partition_key: str) -> dict[str, Any]:
        key = (partition_key, item)
        if key not in self.documents:
            raise KeyError(item)
        return self.documents[key]

    def upsert_item(self, document: dict[str, Any]) -> None:
        self.upserted = document
        self.documents[(document["run_id"], document["id"])] = document

    def query_items(self, **kwargs: Any) -> list[dict[str, Any]]:
        parameters = kwargs.get("parameters", [])
        values = {item["name"]: item["value"] for item in parameters}
        run_id = values.get("@run_id")
        build_id = values.get("@build_id")
        artifact_type = values.get("@artifact_type")
        docs = list(self.documents.values())
        if run_id is not None:
            return [doc for doc in docs if doc["run_id"] == run_id]
        return [
            doc
            for doc in docs
            if doc["build_id"] == build_id and doc["artifact_type"] == artifact_type
        ]


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "DOD_STORAGE_BACKEND": "cosmos",
        "COSMOS_AUTH_MODE": "emulator_key",
        "COSMOS_ENDPOINT": "https://localhost:8081",
        "COSMOS_DATABASE": "dod_agent_local",
        "COSMOS_CONTAINER": "dod_runs",
        "COSMOS_KEY": "local-test-key",
    }
    values.update(overrides)
    return Settings(**values)


def test_cosmos_config_requires_key_for_key_modes() -> None:
    with pytest.raises(ValueError, match="COSMOS_KEY"):
        _required_cosmos_config(_settings(COSMOS_KEY=None, COSMOS_AUTH_MODE="emulator_key"))
    with pytest.raises(ValueError, match="COSMOS_KEY"):
        _required_cosmos_config(_settings(COSMOS_KEY=None, COSMOS_AUTH_MODE="key"))


def test_cosmos_config_default_credential_does_not_require_key() -> None:
    endpoint, credential, database, container = _required_cosmos_config(
        _settings(COSMOS_AUTH_MODE="default_credential", COSMOS_KEY=None)
    )

    assert endpoint == "https://localhost:8081"
    assert credential is not None
    assert database == "dod_agent_local"
    assert container == "dod_runs"


def test_cosmos_document_id_and_partition_key() -> None:
    assert CosmosArtifactStore.document_id("run-1", "run_summary") == "run-1:run_summary"
    assert COSMOS_PARTITION_KEY == "/run_id"


def test_save_load_and_list_with_mocked_container() -> None:
    container = FakeContainer()
    store = CosmosArtifactStore(_settings())
    store._container = container

    reference = store.save_artifact("run-1", 123, "run_summary", {"status": "completed"})

    assert reference == "cosmos://dod_runs/run-1/run_summary"
    assert container.upserted is not None
    assert container.upserted["id"] == "run-1:run_summary"
    assert container.upserted["schema_version"] == "1.0"
    assert store.load_artifact("run-1", "run_summary") == {"status": "completed"}
    assert store.load_artifact_by_build_id(123, "run_summary") == {"status": "completed"}
    assert store.list_artifacts("run-1") == ["run_summary"]
