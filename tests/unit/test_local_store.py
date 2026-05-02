"""Tests for local JSON storage abstraction."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.utils.config import Settings


def test_local_store_save_and_load_json(tmp_path: Path) -> None:
    """Store should save/load UTF-8 JSON under DATA_DIR."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    written_path = store.save_json(
        "raw/123/build.json",
        {"id": 123, "at": datetime(2026, 1, 1, tzinfo=UTC)},
    )

    loaded = store.load_json("raw/123/build.json")
    path_matches = written_path.endswith("raw\\123\\build.json") or written_path.endswith(
        "raw/123/build.json"
    )
    assert path_matches
    assert loaded["id"] == 123
    assert loaded["at"].startswith("2026-01-01")


def test_local_store_ensure_dirs_and_raw_path(tmp_path: Path) -> None:
    """Store should ensure run dirs and build canonical raw path."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    run_dir = store.ensure_run_dirs(42)
    expected_path = store.raw_path(42, "timeline.json")

    assert run_dir.exists()
    assert "raw" in expected_path
    assert "42" in expected_path


def test_local_store_normalized_helpers(tmp_path: Path) -> None:
    """Store should support normalized output helpers."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    normalized_path = store.normalized_path(9, "canonical.json")
    written = store.save_normalized_json(9, "canonical.json", {"build_id": 9})
    loaded = store.load_json("normalized/9/canonical.json")

    assert "normalized" in normalized_path
    assert written.endswith("canonical.json")
    assert loaded["build_id"] == 9


def test_local_store_load_raw_bundle(tmp_path: Path) -> None:
    """Store should load raw bundle by build id helper."""

    store = LocalJsonStore(Settings(DATA_DIR=tmp_path))
    store.save_json("raw/501/raw_bundle.json", {"build_id": 501, "raw": {}})

    payload = store.load_raw_bundle(501)
    assert payload["build_id"] == 501

