"""CLI entrypoint for Phase 6 ServiceNow payload validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

try:
    from backend.app.models.validated_outputs import ValidatedDodOutput
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.services.validation.service import validate_and_assemble_outputs
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.models.validated_outputs import ValidatedDodOutput
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.services.validation.service import validate_and_assemble_outputs
    from backend.app.utils.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and assemble ServiceNow-ready DoD payload."
    )
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--llm-outputs", type=str, default=None)
    parser.add_argument("--evidence-bundle", type=str, default=None)
    parser.add_argument("--allow-llm-repair", action="store_true")
    return parser


def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    """Load inputs, validate, persist Phase 6 artifacts, and return safe summary."""

    store = LocalJsonStore(get_settings())
    llm_outputs, llm_path = _load_llm_outputs(args, store)
    evidence_bundle, evidence_path = _load_evidence_bundle(args, store)
    validated = validate_and_assemble_outputs(
        build_id=args.build_id,
        llm_outputs=llm_outputs,
        evidence_bundle=evidence_bundle,
        source_llm_outputs_path=llm_path,
        source_evidence_bundle_path=evidence_path,
        allow_llm_repair=bool(args.allow_llm_repair),
    )
    output_paths = persist_outputs(store, args.build_id, validated)
    return build_summary(validated, output_paths)


def persist_outputs(
    store: LocalJsonStore,
    build_id: int,
    validated: ValidatedDodOutput,
) -> dict[str, str]:
    """Persist validated output, flat payload, confidence, and traceability artifacts."""

    traceability_payload = (
        validated.traceability_report.model_dump(mode="json")
        if validated.traceability_report is not None
        else {}
    )

    return {
        "validated_output_path": store.save_validated_output_json(
            build_id, validated.model_dump(mode="json")
        ),
        "service_now_payload_path": store.save_service_now_payload_json(
            build_id, validated.service_now_payload.model_dump(mode="json")
        ),
        "confidence_path": store.save_confidence_json(
            build_id, validated.confidence.model_dump(mode="json")
        ),
        "traceability_report_path": store.save_traceability_report_json(
            build_id, traceability_payload
        ),
    }


def build_summary(validated: ValidatedDodOutput, output_paths: dict[str, str]) -> dict[str, Any]:
    """Build a compact summary that excludes generated field text and evidence payloads."""

    issue_counts = {"info": 0, "warning": 0, "error": 0}
    for issue in validated.validation_issues:
        issue_counts[issue.severity] += 1
    raw_reference_leakage_count = sum(
        1 for issue in validated.validation_issues if issue.code == "RAW_REFERENCE_LEAKAGE"
    )
    return {
        "build_id": validated.build_id,
        "is_valid": validated.is_valid,
        "issue_counts": issue_counts,
        "raw_reference_leakage_issue_count": raw_reference_leakage_count,
        "confidence": {
            "overall": validated.confidence.overall,
            "bucket_1": validated.confidence.bucket_1,
            "bucket_2": validated.confidence.bucket_2,
            "bucket_3": validated.confidence.bucket_3,
        },
        "output_paths": output_paths,
    }


def format_summary(summary: dict[str, Any]) -> str:
    """Render safe CLI output."""

    paths = summary["output_paths"]
    return "\n".join(
        [
            "ServiceNow payload validation summary",
            f"- build_id: {summary['build_id']}",
            f"- valid: {summary['is_valid']}",
            f"- issue_counts: {summary['issue_counts']}",
            (
                "- raw_reference_leakage_issue_count: "
                f"{summary.get('raw_reference_leakage_issue_count', 0)}"
            ),
            f"- confidence: {summary['confidence']}",
            f"- validated_output_path: {paths['validated_output_path']}",
            f"- service_now_payload_path: {paths['service_now_payload_path']}",
            f"- traceability_report_path: {paths['traceability_report_path']}",
            f"- confidence_path: {paths['confidence_path']}",
        ]
    )


def _load_llm_outputs(
    args: argparse.Namespace,
    store: LocalJsonStore,
) -> tuple[dict[str, Any], str]:
    if args.llm_outputs:
        path = args.llm_outputs
        return _read_json_object(Path(path)), path
    path = store.output_path(args.build_id, "llm_outputs.json")
    return store.load_llm_outputs(args.build_id), path


def _load_evidence_bundle(
    args: argparse.Namespace,
    store: LocalJsonStore,
) -> tuple[dict[str, Any], str]:
    if args.evidence_bundle:
        path = args.evidence_bundle
        return _read_json_object(Path(path)), path
    path = store.evidence_path(args.build_id, "evidence_bundle.json")
    return store.load_evidence_bundle(args.build_id), path


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Input JSON must be an object: {path}")
    return payload


def main() -> int:
    args = _build_parser().parse_args()
    try:
        summary = run_validation(args)
    except FileNotFoundError as exc:
        print(f"ServiceNow payload validation failed: input file not found. {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"ServiceNow payload validation failed: input file is invalid JSON. {exc}")
        return 3
    except (ValueError, ValidationError) as exc:
        print(f"ServiceNow payload validation failed: {exc}")
        return 4

    print(format_summary(summary))
    return 5 if summary["issue_counts"]["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
