"""Tests for the LangGraph SDK invocation helper."""

from __future__ import annotations

import argparse

from pytest import CaptureFixture, MonkeyPatch
from scripts import invoke_dod_langgraph


def test_build_structured_input_from_args() -> None:
    payload = invoke_dod_langgraph.build_structured_input(
        argparse.Namespace(
            organization="org",
            project="proj",
            build_id=123,
            mode="pipeline",
            correlation_id="corr",
        )
    )

    assert payload == {
        "organization": "org",
        "project": "proj",
        "build_id": 123,
        "mode": "pipeline",
        "correlation_id": "corr",
        "source": "langgraph-sdk-script",
        "metadata": {},
    }


def test_missing_url_produces_helpful_failure(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.delenv("DOD_LANGGRAPH_URL", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "invoke_dod_langgraph.py",
            "--organization",
            "org",
            "--project",
            "proj",
            "--build-id",
            "123",
        ],
    )

    assert invoke_dod_langgraph.main() == 2
    assert "DOD_LANGGRAPH_URL is required" in capsys.readouterr().out


def test_safe_summary_does_not_include_full_payload() -> None:
    rendered = invoke_dod_langgraph.format_safe_summary(
        {
            "run_id": "run-1",
            "build_id": 123,
            "status": "completed",
            "service_now_payload": {"change_description": "secret business text"},
            "rule_evaluation_summary": {"recommended_status": "completed"},
            "artifact_paths": {"run_summary": "summary.json"},
        }
    )

    assert "run-1" in rendered
    assert "completed" in rendered
    assert "run_summary" in rendered
    assert "secret business text" not in rendered
    assert "change_description" not in rendered
