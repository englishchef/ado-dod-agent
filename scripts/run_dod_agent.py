"""CLI entrypoint for Phase 7A LangGraph DoD agent orchestration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from backend.app.models.run_summary import DodRunSummary
    from backend.app.services.orchestration.dod_run_service import run_dod_agent
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.models.run_summary import DodRunSummary
    from backend.app.services.orchestration.dod_run_service import run_dod_agent
    from backend.app.utils.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Phase 7A DoD agent workflow.")
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--organization", type=str, default=None)
    parser.add_argument("--project", type=str, default=None)
    parser.add_argument("--mode", type=str, default="local")
    parser.add_argument("--confidence-threshold", type=float, default=None)
    parser.add_argument("--high-risk-confidence-threshold", type=float, default=None)
    return parser


def run_from_args(args: argparse.Namespace) -> DodRunSummary:
    """Resolve settings-backed defaults and run the orchestration service."""

    settings = get_settings()
    organization = args.organization or settings.ADO_ORGANIZATION
    project = args.project or settings.ADO_PROJECT
    if not organization:
        raise ValueError("organization is required via --organization or ADO_ORGANIZATION.")
    if not project:
        raise ValueError("project is required via --project or ADO_PROJECT.")

    input_data: dict[str, Any] = {
        "organization": organization,
        "project": project,
        "build_id": args.build_id,
        "mode": args.mode or "local",
    }
    if args.confidence_threshold is not None:
        input_data["confidence_threshold"] = args.confidence_threshold
    if args.high_risk_confidence_threshold is not None:
        input_data["high_risk_confidence_threshold"] = args.high_risk_confidence_threshold
    return run_dod_agent(input_data)


def format_summary(
    summary: DodRunSummary,
    routing_payload: dict[str, Any] | None = None,
) -> str:
    """Render a safe summary without generated field text, evidence, or credentials."""

    paths = summary.artifact_paths
    overall = _overall_confidence(summary.confidence)
    evidence_quality = _evidence_quality_summary(routing_payload)
    prompt_strategy = _prompt_strategy_summary(routing_payload)
    risk_tier = _risk_tier_summary(routing_payload)
    lines = [
        "DoD agent run summary",
        f"- run_id: {summary.run_id}",
        f"- build_id: {summary.build_id}",
        f"- status: {summary.status}",
        f"- overall_confidence: {overall if overall is not None else 'n/a'}",
        f"- evidence_quality: {evidence_quality}",
        f"- risk_tier: {risk_tier}",
        f"- prompt_strategies: {prompt_strategy}",
        f"- warning_count: {len(summary.warnings)}",
        f"- error_count: {len(summary.errors)}",
        f"- raw_bundle: {paths.get('raw_bundle')}",
        f"- canonical: {paths.get('canonical')}",
        f"- evidence_bundle: {paths.get('evidence_bundle')}",
        f"- llm_outputs: {paths.get('llm_outputs')}",
        f"- validated_output: {paths.get('validated_output')}",
        f"- service_now_payload: {paths.get('service_now_payload')}",
        f"- confidence: {paths.get('confidence')}",
        f"- routing_decisions: {paths.get('routing_decisions')}",
        f"- run_summary: {paths.get('run_summary')}",
    ]
    return "\n".join(lines)


def main() -> int:
    args = _build_parser().parse_args()
    try:
        summary = run_from_args(args)
    except ValueError as exc:
        print(f"DoD agent run failed: {exc}")
        return 2

    print(format_summary(summary, _load_routing_payload(summary)))
    return 1 if summary.status == "failed" else 0


def _overall_confidence(confidence: dict[str, Any] | None) -> float | None:
    if not isinstance(confidence, dict):
        return None
    value = confidence.get("overall")
    if isinstance(value, int | float):
        return round(float(value), 4)
    return None


def _load_routing_payload(summary: DodRunSummary) -> dict[str, Any] | None:
    path = summary.artifact_paths.get("routing_decisions")
    if not path:
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _evidence_quality_summary(payload: dict[str, Any] | None) -> dict[str, Any] | str:
    evidence_quality = payload.get("evidence_quality") if isinstance(payload, dict) else None
    if not isinstance(evidence_quality, dict):
        return "n/a"
    return {
        "bucket_1": evidence_quality.get("bucket_1_quality"),
        "bucket_2": evidence_quality.get("bucket_2_quality"),
        "bucket_3": evidence_quality.get("bucket_3_quality"),
    }


def _prompt_strategy_summary(payload: dict[str, Any] | None) -> dict[str, Any] | str:
    prompt_strategy = payload.get("prompt_strategy") if isinstance(payload, dict) else None
    if not isinstance(prompt_strategy, dict):
        return "n/a"
    return {
        "bucket_1": prompt_strategy.get("bucket_1_strategy"),
        "bucket_2": prompt_strategy.get("bucket_2_strategy"),
        "bucket_3": prompt_strategy.get("bucket_3_strategy"),
    }


def _risk_tier_summary(payload: dict[str, Any] | None) -> str:
    risk_tier = payload.get("risk_tier") if isinstance(payload, dict) else None
    if not isinstance(risk_tier, dict):
        return "n/a"
    value = risk_tier.get("risk_tier")
    return str(value) if value else "n/a"


if __name__ == "__main__":
    raise SystemExit(main())
