"""CLI entrypoint for Phase-4 deterministic evidence bucket generation."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

try:
    from backend.app.models.canonical import CanonicalDodDocument
    from backend.app.services.evidence.builder import build_evidence_bundle, build_evidence_summary
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.app.models.canonical import CanonicalDodDocument
    from backend.app.services.evidence.builder import build_evidence_bundle, build_evidence_summary
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build deterministic evidence buckets.")
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--canonical", type=str, default=None)
    parser.add_argument("--max-items-per-section", type=int, default=10)
    return parser


def format_summary(summary: dict[str, Any]) -> str:
    """Render a compact and safe CLI summary."""

    output_paths = summary.get("output_paths", {})
    lines = [
        "Evidence generation summary",
        f"- build_id: {summary.get('build_id')}",
        f"- pipeline_name: {summary.get('pipeline_name')}",
        f"- bucket_1_counts: {summary.get('bucket_1_counts', {})}",
        f"- bucket_2_counts: {summary.get('bucket_2_counts', {})}",
        f"- bucket_3_counts: {summary.get('bucket_3_counts', {})}",
        f"- evidence_gap_counts: {summary.get('evidence_gap_counts', {})}",
        f"- truncation_applied: {summary.get('truncation_applied', False)}",
        f"- bucket_1_change_intent_path: {output_paths.get('bucket_1_change_intent_path')}",
        (
            "- bucket_2_execution_validation_path: "
            f"{output_paths.get('bucket_2_execution_validation_path')}"
        ),
        f"- bucket_3_rollback_risk_path: {output_paths.get('bucket_3_rollback_risk_path')}",
        f"- evidence_bundle_path: {output_paths.get('evidence_bundle_path')}",
    ]
    return "\n".join(lines)


async def _run_from_args(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    store = LocalJsonStore(settings)

    canonical_path = args.canonical or store.normalized_path(args.build_id, "canonical.json")
    canonical_payload = json.loads(Path(canonical_path).read_text(encoding="utf-8"))
    if not isinstance(canonical_payload, dict):
        raise ValueError("Canonical input must be a JSON object.")
    canonical_payload["build_id"] = args.build_id

    canonical_document = CanonicalDodDocument.model_validate(canonical_payload)
    bundle = build_evidence_bundle(
        canonical=canonical_document,
        source_path=canonical_path,
        max_items_per_section=args.max_items_per_section,
    )

    bucket_1_path = store.save_evidence_json(
        build_id=args.build_id,
        filename="bucket_1_change_intent.json",
        payload=bundle.bucket_1.model_dump(mode="json"),
    )
    bucket_2_path = store.save_evidence_json(
        build_id=args.build_id,
        filename="bucket_2_execution_validation.json",
        payload=bundle.bucket_2.model_dump(mode="json"),
    )
    bucket_3_path = store.save_evidence_json(
        build_id=args.build_id,
        filename="bucket_3_rollback_risk.json",
        payload=bundle.bucket_3.model_dump(mode="json"),
    )
    bundle_path = store.save_evidence_json(
        build_id=args.build_id,
        filename="evidence_bundle.json",
        payload=bundle.model_dump(mode="json"),
    )

    return build_evidence_summary(
        bundle=bundle,
        bucket_paths={
            "bucket_1_change_intent_path": bucket_1_path,
            "bucket_2_execution_validation_path": bucket_2_path,
            "bucket_3_rollback_risk_path": bucket_3_path,
            "evidence_bundle_path": bundle_path,
        },
    )


def main() -> int:
    args = _build_parser().parse_args()
    try:
        summary = asyncio.run(_run_from_args(args))
    except FileNotFoundError:
        print(
            "Evidence generation failed: "
            f"canonical file not found for build_id={args.build_id}."
        )
        return 2
    except json.JSONDecodeError:
        print(
            "Evidence generation failed: "
            f"canonical file is invalid JSON for build_id={args.build_id}."
        )
        return 3
    except ValueError as exc:
        print(f"Evidence generation failed: {exc}")
        return 4

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
