"""Tests for local JSON storage abstraction."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.storage.local_store import LocalJsonStore


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
