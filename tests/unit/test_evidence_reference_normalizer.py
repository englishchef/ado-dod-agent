"""Tests for friendly evidence source reference normalization."""

from __future__ import annotations

from backend.app.services.evidence.reference_normalizer import (
    build_source_ref_map_entry,
    normalize_source_ref,
    safe_ref_name,
)


def test_work_item_source_ref_becomes_friendly_ref() -> None:
    friendly_ref, entry = normalize_source_ref(
        "work_item",
        {"id": 12345, "title": "Upgrade checkout flow"},
        "raw.work_items.value[0]",
    )

    assert friendly_ref == "work_item:12345"
    assert entry.original_ref == "raw.work_items.value[0]"
    assert entry.display_name == "Upgrade checkout flow"


def test_commit_source_ref_becomes_short_sha_ref() -> None:
    friendly_ref, entry = normalize_source_ref(
        "commit",
        {"id": "9f3a21b8e7", "message": "Upgrade Hazelcast version"},
        "raw.changes.value[3]",
    )

    assert friendly_ref == "commit:9f3a21b"
    assert entry.source_type == "commit"
    assert entry.original_ref == "raw.changes.value[3]"


def test_pipeline_task_source_ref_uses_safe_name() -> None:
    friendly_ref, _ = normalize_source_ref(
        "pipeline_task",
        {"name": "Run Functional Tests"},
        "raw.timeline.records[10]",
    )

    assert friendly_ref == "pipeline_task:Run_Functional_Tests"


def test_test_run_source_ref_uses_safe_name_or_id() -> None:
    friendly_ref, _ = normalize_source_ref(
        "test_run",
        {"id": 42, "name": "Regression Suite"},
        "raw.test_runs.value[0]",
    )

    assert friendly_ref == "test_run:Regression_Suite"


def test_artifact_source_ref_uses_safe_name() -> None:
    friendly_ref, _ = normalize_source_ref(
        "artifact",
        {"name": "drop"},
        "raw.artifacts.value[0]",
    )

    assert friendly_ref == "artifact:drop"


def test_safe_ref_name_trims_spaces_and_removes_unsupported_characters() -> None:
    assert safe_ref_name(" Deploy to DEV / slot ") == "Deploy_to_DEV_slot"


def test_build_source_ref_map_entry() -> None:
    entry = build_source_ref_map_entry(
        friendly_ref="pipeline_stage:Deploy_to_DEV",
        original_ref="raw.timeline.records[2]",
        source_type="stage",
        display_name="Deploy to DEV",
    )

    assert entry.friendly_ref == "pipeline_stage:Deploy_to_DEV"
    assert entry.original_ref == "raw.timeline.records[2]"
