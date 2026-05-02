"""Tests for Phase-3 normalization CLI helpers."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from backend.app.utils.config import Settings
from pytest import MonkeyPatch
from scripts import normalize_raw_metadata


def test_normalize_script_loads_raw_bundle_and_writes_canonical(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI internal runner should read raw bundle and persist canonical output."""

    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw" / "321"
    raw_dir.mkdir(parents=True)
    raw_bundle = {
        "build_id": 321,
        "organization": "org",
        "project": "proj",
        "status": "completed",
        "raw": {"build": {"id": 321}},
    }
    (raw_dir / "raw_bundle.json").write_text(json.dumps(raw_bundle), encoding="utf-8")
    monkeypatch.setattr(normalize_raw_metadata, "get_settings", lambda: Settings(DATA_DIR=data_dir))

    args = argparse.Namespace(build_id=321, raw_bundle=None)
    summary = asyncio.run(normalize_raw_metadata._run_from_args(args))

    canonical_path = Path(summary["canonical_path"])
    assert canonical_path.exists()
    canonical_payload = json.loads(canonical_path.read_text(encoding="utf-8"))
    assert canonical_payload["build_id"] == 321
    assert canonical_payload["run_context"]["build_id"] == 321
    rendered = normalize_raw_metadata.format_summary(summary)
    assert "Canonical normalization summary" in rendered
