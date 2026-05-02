"""Tests for Phase-4 evidence generation CLI helpers."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.models.canonical import (
    CanonicalDodDocument,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)
from backend.app.utils.config import Settings
from pytest import MonkeyPatch
from scripts import build_evidence_buckets


def _canonical_document(build_id: int) -> CanonicalDodDocument:
    return CanonicalDodDocument(
        build_id=build_id,
        organization="org",
        project="proj",
        generated_at=datetime.now(UTC),
        source_raw_bundle_path=f"data/raw/{build_id}/raw_bundle.json",
        run_context=RunContext(build_id=build_id, pipeline_name="Pipeline"),
        change_context=ChangeContext(),
        execution_context=ExecutionContext(),
        quality_context=QualityContext(),
        risk_context=RiskContext(),
        normalization_metadata=NormalizationMetadata(),
    )


def test_build_evidence_script_loads_canonical_and_writes_outputs(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """CLI internal runner should read canonical input and persist evidence files."""

    data_dir = tmp_path / "data"
    normalized_dir = data_dir / "normalized" / "321"
    normalized_dir.mkdir(parents=True)
    canonical = _canonical_document(321)
    (normalized_dir / "canonical.json").write_text(
        canonical.model_dump_json(indent=2),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_evidence_buckets, "get_settings", lambda: Settings(DATA_DIR=data_dir))

    args = argparse.Namespace(build_id=321, canonical=None, max_items_per_section=10)
    summary = asyncio.run(build_evidence_buckets._run_from_args(args))

    bundle_path = Path(summary["output_paths"]["evidence_bundle_path"])
    assert bundle_path.exists()
    bundle_payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert bundle_payload["build_id"] == 321
    rendered = build_evidence_buckets.format_summary(summary)
    assert "Evidence generation summary" in rendered
    assert "run_context" not in rendered
