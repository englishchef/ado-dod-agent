"""CLI entrypoint for Phase 9 deterministic rule evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from backend.app.models.rules import RuleEvaluation
    from backend.app.services.rules.rule_engine import evaluate_rules
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.models.rules import RuleEvaluation
    from backend.app.services.rules.rule_engine import evaluate_rules
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate deterministic post-generation rules.")
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--evidence-bundle", type=str, default=None)
    parser.add_argument("--service-now-payload", type=str, default=None)
    parser.add_argument("--llm-outputs", type=str, default=None)
    parser.add_argument("--validated-output", type=str, default=None)
    parser.add_argument("--confidence", type=str, default=None)
    parser.add_argument("--routing-decisions", type=str, default=None)
    parser.add_argument("--traceability-report", type=str, default=None)
    return parser


def run_evaluation(args: argparse.Namespace) -> dict[str, Any]:
    """Load artifacts, evaluate rules, persist output, and return safe summary."""

    store = LocalJsonStore(get_settings())
    evidence_bundle, evidence_path = _load_required(
        args.evidence_bundle,
        store.evidence_path(args.build_id, "evidence_bundle.json"),
        lambda: store.load_evidence_bundle(args.build_id),
    )
    service_now_payload, payload_path = _load_required(
        args.service_now_payload,
        store.output_path(args.build_id, "service_now_payload.json"),
        lambda: store.load_service_now_payload(args.build_id),
    )
    llm_outputs, llm_path = _load_optional(
        args.llm_outputs,
        store.output_path(args.build_id, "llm_outputs.json"),
        lambda: store.load_llm_outputs(args.build_id),
    )
    validated_output, validated_path = _load_optional(
        args.validated_output,
        store.output_path(args.build_id, "validated_output.json"),
        lambda: store.load_validated_output(args.build_id),
    )
    confidence, confidence_path = _load_optional(
        args.confidence,
        store.output_path(args.build_id, "confidence.json"),
        lambda: store.load_confidence(args.build_id),
    )
    routing_decisions, routing_path = _load_optional(
        args.routing_decisions,
        store.output_path(args.build_id, "routing_decisions.json"),
        lambda: store.load_routing_decisions(args.build_id),
    )
    traceability_report, traceability_path = _load_optional(
        args.traceability_report,
        store.output_path(args.build_id, "traceability_report.json"),
        lambda: store.load_traceability_report(args.build_id),
    )
    source_paths = {
        "evidence_bundle": evidence_path,
        "service_now_payload": payload_path,
        "llm_outputs": llm_path,
        "validated_output": validated_path,
        "confidence": confidence_path,
        "routing_decisions": routing_path,
        "traceability_report": traceability_path,
    }
    evaluation = evaluate_rules(
        build_id=args.build_id,
        evidence_bundle=evidence_bundle,
        service_now_payload=service_now_payload,
        llm_outputs=llm_outputs,
        validated_output=validated_output,
        confidence=confidence,
        routing_decisions=routing_decisions,
        traceability_report=traceability_report,
        source_paths={key: value for key, value in source_paths.items() if value},
    )
    output_path = store.save_rule_evaluation_json(
        args.build_id,
        evaluation.model_dump(mode="json"),
    )
    return build_summary(evaluation, output_path)


def build_summary(evaluation: RuleEvaluation, output_path: str) -> dict[str, Any]:
    """Build a compact rule evaluation summary."""

    return {
        "build_id": evaluation.build_id,
        "test_completeness_score": evaluation.test_completeness_score.overall_score,
        "highest_severity": evaluation.summary.highest_severity,
        "recommended_status": evaluation.summary.recommended_status,
        "triggered_rule_count": evaluation.summary.triggered_rule_count,
        "severity_counts": {
            "info": evaluation.summary.info_count,
            "warning": evaluation.summary.warning_count,
            "review": evaluation.summary.review_count,
            "error": evaluation.summary.error_count,
        },
        "output_path": output_path,
    }


def format_summary(summary: dict[str, Any]) -> str:
    """Render safe CLI output without payload or evidence content."""

    return "\n".join(
        [
            "Rule evaluation summary",
            f"- build_id: {summary['build_id']}",
            f"- test_completeness_score: {summary['test_completeness_score']}",
            f"- highest_severity: {summary['highest_severity']}",
            f"- recommended_status: {summary['recommended_status']}",
            f"- triggered_rule_count: {summary['triggered_rule_count']}",
            f"- severity_counts: {summary['severity_counts']}",
            f"- rule_evaluation_path: {summary['output_path']}",
        ]
    )


def main() -> int:
    args = _build_parser().parse_args()
    try:
        summary = run_evaluation(args)
    except FileNotFoundError as exc:
        print(f"Rule evaluation failed: required input file not found. {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"Rule evaluation failed: input file is invalid JSON. {exc}")
        return 3
    except ValueError as exc:
        print(f"Rule evaluation failed: {exc}")
        return 4
    print(format_summary(summary))
    return 1 if summary["recommended_status"] == "failed" else 0


def _load_required(
    explicit_path: str | None,
    default_path: str,
    load_default: Any,
) -> tuple[dict[str, Any], str]:
    if explicit_path:
        return _read_json_object(Path(explicit_path)), explicit_path
    return load_default(), default_path


def _load_optional(
    explicit_path: str | None,
    default_path: str,
    load_default: Any,
) -> tuple[dict[str, Any] | None, str]:
    if explicit_path:
        return _read_json_object(Path(explicit_path)), explicit_path
    try:
        return load_default(), default_path
    except FileNotFoundError:
        return None, ""


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Input JSON must be an object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
