"""Tests for the Phase 7A run_dod_agent CLI."""

from __future__ import annotations

from datetime import UTC, datetime

from backend.app.models.run_summary import DodRunSummary, RunIssue
from backend.app.utils.config import Settings
from pytest import CaptureFixture, MonkeyPatch
from scripts import run_dod_agent


def _summary(status: str) -> DodRunSummary:
    return DodRunSummary(
        run_id="dod-run-20260527T010203Z-9",
        build_id=9,
        organization="org",
        project="proj",
        status=status,
        started_at=datetime(2026, 5, 27, tzinfo=UTC),
        completed_at=datetime(2026, 5, 27, 0, 1, tzinfo=UTC),
        confidence={"overall": 0.76},
        artifact_paths={
            "raw_bundle": "raw.json",
            "canonical": "canonical.json",
            "evidence_bundle": "evidence.json",
            "llm_outputs": "llm.json",
            "validated_output": "validated.json",
            "service_now_payload": "payload.json",
            "confidence": "confidence.json",
            "routing_decisions": "routing.json",
            "run_summary": "summary.json",
        },
        warnings=[RunIssue(severity="warning", code="gap", message="gap", phase="evidence")],
        errors=[],
    )


def test_run_dod_agent_script_prints_safe_summary(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        run_dod_agent,
        "get_settings",
        lambda: Settings(ADO_ORGANIZATION="org", ADO_PROJECT="proj"),
    )
    monkeypatch.setattr(run_dod_agent, "run_dod_agent", lambda _: _summary("completed"))
    monkeypatch.setattr("sys.argv", ["run_dod_agent.py", "--build-id", "9"])

    assert run_dod_agent.main() == 0
    rendered = capsys.readouterr().out.lower()

    assert "dod agent run summary" in rendered
    assert "overall_confidence: 0.76" in rendered
    assert "evidence_quality:" in rendered
    assert "risk_tier:" in rendered
    assert "prompt_strategies:" in rendered
    assert "routing_decisions: routing.json" in rendered
    assert "token" not in rendered
    assert "authorization" not in rendered
    assert "bearer" not in rendered
    assert "change_description" not in rendered


def test_run_dod_agent_script_exits_nonzero_for_failed(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_dod_agent,
        "get_settings",
        lambda: Settings(ADO_ORGANIZATION="org", ADO_PROJECT="proj"),
    )
    monkeypatch.setattr(run_dod_agent, "run_dod_agent", lambda _: _summary("failed"))
    monkeypatch.setattr("sys.argv", ["run_dod_agent.py", "--build-id", "9"])

    assert run_dod_agent.main() == 1


def test_run_dod_agent_script_exits_zero_for_needs_review(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_dod_agent,
        "get_settings",
        lambda: Settings(ADO_ORGANIZATION="org", ADO_PROJECT="proj"),
    )
    monkeypatch.setattr(run_dod_agent, "run_dod_agent", lambda _: _summary("needs_review"))
    monkeypatch.setattr("sys.argv", ["run_dod_agent.py", "--build-id", "9"])

    assert run_dod_agent.main() == 0
