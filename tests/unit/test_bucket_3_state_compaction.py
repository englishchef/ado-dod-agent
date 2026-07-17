"""Bucket 3 recursive evidence remains in artifacts, not LangGraph state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from backend.app.graphs import nodes
from backend.app.models.canonical import (
    CanonicalDodDocument,
    CanonicalJob,
    CanonicalStage,
    CanonicalTask,
    ChangeContext,
    ExecutionContext,
    NormalizationMetadata,
    QualityContext,
    RiskContext,
    RunContext,
)
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def _canonical() -> CanonicalDodDocument:
    started = datetime(2026, 7, 17, tzinfo=UTC)
    return CanonicalDodDocument(
        build_id=7,
        organization="org",
        project="proj",
        generated_at=started,
        run_context=RunContext(build_id=7, repository_name="sample-service"),
        change_context=ChangeContext(),
        execution_context=ExecutionContext(
            stages=[
                CanonicalStage(
                    id="uat",
                    name="UAT",
                    state="completed",
                    result="succeeded",
                    start_time=started,
                    finish_time=started + timedelta(minutes=87),
                )
            ],
            jobs=[CanonicalJob(id="job", parent_id="uat", name="Deployment Job")],
            tasks=[
                CanonicalTask(
                    id="upgrade",
                    parent_id="job",
                    name="Apply Solution Upgrade",
                    state="completed",
                    result="succeeded",
                ),
                CanonicalTask(
                    id="lookup",
                    parent_id="job",
                    name="Get Base Solution Versions",
                    state="completed",
                    result="succeeded",
                    log_summary="raw task log must stay out of state",
                ),
            ],
        ),
        quality_context=QualityContext(),
        risk_context=RiskContext(),
        normalization_metadata=NormalizationMetadata(),
    )


class _Store:
    def __init__(self, canonical: CanonicalDodDocument) -> None:
        self.canonical = canonical
        self.saved: dict[str, Any] = {}

    def normalized_path(self, build_id: int, filename: str) -> str:
        return f"cosmos://run-{build_id}/canonical"

    def load_canonical(self, build_id: int) -> dict[str, Any]:
        return self.canonical.model_dump(mode="json")

    def save_evidence_json(self, build_id: int, filename: str, payload: Any) -> str:
        self.saved[filename] = payload
        return f"cosmos://run-{build_id}/{filename.removesuffix('.json')}"


def test_recursive_details_are_persisted_while_state_receives_only_summary(
    monkeypatch: MonkeyPatch,
) -> None:
    store = _Store(_canonical())
    monkeypatch.setattr(nodes, "get_settings", lambda: Settings(DOD_STORAGE_BACKEND="local_json"))
    monkeypatch.setattr(nodes, "LocalJsonStore", lambda *_: store)
    state: nodes.DodGraphState = {
        "run_id": "run-7",
        "build_id": 7,
        "organization": "org",
        "project": "proj",
        "mode": "pipeline",
        "status": "started",
        "artifact_paths": {"canonical": "cosmos://run-7/canonical"},
        "warnings": [],
        "errors": [],
    }

    update = nodes.build_evidence_buckets_node(state)

    artifact = store.saved["bucket_3_rollback_risk.json"]
    derivation = artifact["backout_step_derivation"]
    assert derivation["recursive_traversal_used"] is True
    assert derivation["descendant_count"] == 3
    assert derivation["source_tasks"]
    assert derivation["ignored_tasks"]

    summary = update["bucket_3_summary"]
    assert summary["selected_environment"] == "UAT"
    assert summary["estimated_backout_minutes"] == 90
    assert summary["normalized_actions"] == ["solution_upgrade"]
    assert "source_tasks" not in summary
    assert "ignored_tasks" not in summary
    assert "evidence_result" not in update
    rendered = repr(update)
    for forbidden in ("parent_index", "child_index", "visited", "pending", "raw task log"):
        assert forbidden not in rendered

