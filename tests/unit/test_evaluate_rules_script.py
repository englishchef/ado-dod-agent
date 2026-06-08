"""Tests for Phase 9 evaluate_rules CLI helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.utils.config import Settings
from pytest import CaptureFixture, MonkeyPatch
from scripts import evaluate_rules


def _payload() -> dict[str, str]:
    return {
        "change_description": "Deploy service update.",
        "short_change_description": "Deploy service update",
        "justification": "Improve supportability.",
        "testing_performed": "Automated test results were not available.",
        "implementation_plan": "Deploy through the approved release pipeline.",
        "validation_plan": "Validate API health and review monitoring logs.",
        "backout_plan": "Redeploy previous build.",
        "risk_impact_analysis": "No specific risk signals were detected.",
    }


def _evidence() -> dict[str, object]:
    return {
        "bucket_2": {
            "test_evidence": {"total_tests": 0},
            "validation_signals": ["Smoke validation"],
            "artifact_evidence": [{"name": "drop"}],
        },
        "bucket_3": {"risk_flags": {}, "artifact_evidence": [{"name": "drop"}]},
    }


def _write_inputs(data_dir: Path, build_id: int = 5) -> None:
    evidence_dir = data_dir / "evidence" / str(build_id)
    output_dir = data_dir / "output" / str(build_id)
    evidence_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    (evidence_dir / "evidence_bundle.json").write_text(json.dumps(_evidence()), encoding="utf-8")
    (output_dir / "service_now_payload.json").write_text(json.dumps(_payload()), encoding="utf-8")


def test_evaluate_rules_script_loads_fixtures_and_writes_output(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_inputs(data_dir)
    monkeypatch.setattr(evaluate_rules, "get_settings", lambda: Settings(DATA_DIR=data_dir))

    summary = evaluate_rules.run_evaluation(argparse.Namespace(build_id=5, **_empty_args()))

    assert Path(summary["output_path"]).exists()
    assert summary["build_id"] == 5


def test_evaluate_rules_exits_zero_for_needs_review(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    _write_inputs(data_dir)
    monkeypatch.setattr(evaluate_rules, "get_settings", lambda: Settings(DATA_DIR=data_dir))
    monkeypatch.setattr("sys.argv", ["evaluate_rules.py", "--build-id", "5"])

    assert evaluate_rules.main() == 0


def test_evaluate_rules_exits_nonzero_for_failed(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        evaluate_rules,
        "run_evaluation",
        lambda _: {
            "build_id": 5,
            "test_completeness_score": 0.0,
            "highest_severity": "error",
            "recommended_status": "failed",
            "triggered_rule_count": 1,
            "severity_counts": {"info": 0, "warning": 0, "review": 0, "error": 1},
            "output_path": "rule_evaluation.json",
        },
    )
    monkeypatch.setattr("sys.argv", ["evaluate_rules.py", "--build-id", "5"])

    assert evaluate_rules.main() == 1


def test_evaluate_rules_summary_does_not_print_full_payload(
    capsys: CaptureFixture[str],
) -> None:
    rendered = evaluate_rules.format_summary(
        {
            "build_id": 5,
            "test_completeness_score": 0.4,
            "highest_severity": "review",
            "recommended_status": "needs_review",
            "triggered_rule_count": 2,
            "severity_counts": {"info": 0, "warning": 1, "review": 1, "error": 0},
            "output_path": "rule_evaluation.json",
        }
    )
    print(rendered)
    output = capsys.readouterr().out.lower()

    assert "change_description" not in output
    assert "token" not in output
    assert "rule_evaluation_path" in output


def _empty_args() -> dict[str, object]:
    return {
        "evidence_bundle": None,
        "service_now_payload": None,
        "llm_outputs": None,
        "validated_output": None,
        "confidence": None,
        "routing_decisions": None,
        "traceability_report": None,
    }
