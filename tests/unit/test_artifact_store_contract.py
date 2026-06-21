"""Tests for the common artifact store contract."""

from __future__ import annotations

from typing import Any

from backend.app.services.storage.artifact_store import ArtifactStore
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import Settings


def test_local_json_store_satisfies_artifact_store_contract(tmp_path: Any) -> None:
    store: ArtifactStore = LocalJsonStore(Settings(DATA_DIR=tmp_path))

    path = store.save_artifact(
        run_id="run-1",
        build_id=123,
        artifact_type="service_now_payload",
        content={"status": "ok"},
    )

    assert path.endswith("service_now_payload.json")
    assert store.load_artifact_by_build_id(123, "service_now_payload") == {"status": "ok"}
