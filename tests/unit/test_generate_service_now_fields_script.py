"""Tests for the Phase 5B generation CLI helpers."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.models.llm_outputs import (
    Bucket1GeneratedOutput,
    Bucket2GeneratedOutput,
    Bucket3GeneratedOutput,
    CombinedLlmOutputs,
    LlmModelMetadata,
)
from backend.app.utils.config import Settings
from pytest import MonkeyPatch
from scripts import generate_service_now_fields


class DummyClient:
    def __init__(self, **_: Any) -> None:
        pass


def _combined_outputs(build_id: int) -> CombinedLlmOutputs:
    return CombinedLlmOutputs(
        build_id=build_id,
        organization="org",
        project="proj",
        generated_at=datetime.now(UTC),
        source_evidence_bundle_path=f"data/evidence/{build_id}/evidence_bundle.json",
        model_metadata=LlmModelMetadata(
            provider="azure_openai",
            deployment="deployment",
            api_version="2024-10-21",
            auth_mode="entra",
            prompt_versions={"bucket_1": "1.0", "bucket_2": "1.0", "bucket_3": "1.0"},
        ),
        bucket_1=Bucket1GeneratedOutput(
            change_description="Change description",
            short_change_description="Short change",
            justification="Justification",
            evidence_used=["ref1"],
            missing_information=[],
            model_confidence=0.8,
            generation_notes=[],
        ),
        bucket_2=Bucket2GeneratedOutput(
            testing_performed="No automated test results were available.",
            implementation_plan="Implementation plan",
            validation_plan="Validation plan",
            evidence_used=["ref2"],
            missing_information=["tests missing"],
            model_confidence=0.7,
            generation_notes=[],
        ),
        bucket_3=Bucket3GeneratedOutput(
            backout_plan="Backout plan",
            risk_impact_analysis="Risk analysis",
            evidence_used=["ref3"],
            missing_information=["rollback task missing"],
            model_confidence=0.6,
            generation_notes=[],
        ),
    )


def test_script_loads_fixture_bundle_and_writes_outputs(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    evidence_dir = data_dir / "evidence" / "55"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "evidence_bundle.json").write_text(
        json.dumps({"build_id": 55, "bucket_1": {}, "bucket_2": {}, "bucket_3": {}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        generate_service_now_fields,
        "get_settings",
        lambda: Settings(DATA_DIR=data_dir, AZURE_OPENAI_DEPLOYMENT="deployment"),
    )
    monkeypatch.setattr(generate_service_now_fields, "AzureFoundryChatClient", DummyClient)
    monkeypatch.setattr(
        generate_service_now_fields,
        "generate_all_buckets",
        lambda **_: _combined_outputs(55),
    )

    args = argparse.Namespace(
        build_id=55,
        evidence_bundle=None,
        bucket_1=None,
        bucket_2=None,
        bucket_3=None,
    )
    summary = generate_service_now_fields.run_generation(args)

    assert Path(summary["output_paths"]["llm_outputs_path"]).exists()
    assert Path(summary["output_paths"]["bucket_1_output_path"]).exists()
    payload = json.loads(Path(summary["output_paths"]["llm_outputs_path"]).read_text())
    assert payload["bucket_1"]["change_description"] == "Change description"


def test_script_summary_does_not_print_tokens_or_authorization_headers() -> None:
    summary = generate_service_now_fields.build_summary(
        outputs=_combined_outputs(77),
        output_paths={
            "bucket_1_output_path": "bucket1.json",
            "bucket_2_output_path": "bucket2.json",
            "bucket_3_output_path": "bucket3.json",
            "llm_outputs_path": "all.json",
        },
    )

    rendered = generate_service_now_fields.format_summary(summary).lower()

    assert "token" not in rendered
    assert "authorization" not in rendered
    assert "bearer" not in rendered
    assert "change description" not in rendered
