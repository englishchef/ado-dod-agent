"""Tests for Cosmos document_type compatibility fields."""

from __future__ import annotations

from typing import Any

from backend.app.services.storage.cosmos_artifact_store import CosmosArtifactStore
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


def _settings() -> Settings:
    return Settings(
        DOD_STORAGE_BACKEND="cosmos",
        COSMOS_AUTH_MODE="emulator_key",
        COSMOS_ENDPOINT="https://localhost:8081",
        COSMOS_DATABASE="dod_agent_local",
        COSMOS_CONTAINER="dod_runs",
        COSMOS_KEY="local-test-key",
    )


def test_cosmos_artifact_write_includes_artifact_document_type() -> None:
    container = FakeContainer()
    store = CosmosArtifactStore(_settings())
    store._container = container

    store.save_artifact("run-1", 123, "service_now_payload", {"status": "ok"})

    assert container.upserted is not None
    assert container.upserted["id"] == "run-1:service_now_payload"
    assert container.upserted["document_type"] == "artifact"


def test_cosmos_run_summary_write_includes_run_summary_document_type() -> None:
    container = FakeContainer()
    store = CosmosArtifactStore(_settings())
    store._container = container

    store.save_run_summary("run-1", 123, {"status": "completed"})

    assert container.upserted is not None
    assert container.upserted["id"] == "run-1:run_summary"
    assert container.upserted["document_type"] == "run_summary"


def test_cosmos_read_remains_compatible_when_document_type_missing() -> None:
    container = FakeContainer()
    container.documents[("run-1", "run-1:service_now_payload")] = {
        "id": "run-1:service_now_payload",
        "run_id": "run-1",
        "build_id": 123,
        "artifact_type": "service_now_payload",
        "content": {"status": "old"},
        "schema_version": "1.0",
    }
    store = CosmosArtifactStore(_settings())
    store._container = container

    assert store.load_artifact("run-1", "service_now_payload") == {"status": "old"}
