"""CLI entrypoint for Phase-3 canonical normalization."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

try:
    from backend.app.services.normalizers.canonical import (
        build_canonical_summary,
        normalize_raw_bundle,
    )
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from backend.app.services.normalizers.canonical import (
        build_canonical_summary,
        normalize_raw_bundle,
    )
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize raw ADO metadata into canonical JSON.")
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--raw-bundle", type=str, default=None)
    return parser


def format_summary(summary: dict[str, Any]) -> str:
    """Render a safe, compact summary for console output."""

    lines = [
        "Canonical normalization summary",
        f"- build_id: {summary.get('build_id')}",
        f"- pipeline_name: {summary.get('pipeline_name')}",
        f"- source_branch: {summary.get('source_branch')}",
        f"- source_version: {summary.get('source_version')}",
        f"- work_item_count: {summary.get('work_item_count', 0)}",
        f"- commit_count: {summary.get('commit_count', 0)}",
        f"- pull_request_count: {summary.get('pull_request_count', 0)}",
        f"- stage_count: {summary.get('stage_count', 0)}",
        f"- job_count: {summary.get('job_count', 0)}",
        f"- task_count: {summary.get('task_count', 0)}",
        f"- artifact_count: {summary.get('artifact_count', 0)}",
        f"- test_run_count: {summary.get('test_run_count', 0)}",
        f"- failed_test_count: {summary.get('failed_test_count', 0)}",
        f"- risk_flags: {summary.get('risk_flags', [])}",
        f"- canonical_path: {summary.get('canonical_path')}",
    ]
    return "\n".join(lines)


async def _run_from_args(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    store = LocalJsonStore(settings)

    raw_bundle_path = args.raw_bundle or store.raw_path(args.build_id, "raw_bundle.json")
    raw_payload = json.loads(Path(raw_bundle_path).read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("Raw bundle must be a JSON object.")
    raw_payload["build_id"] = args.build_id

    canonical_document = normalize_raw_bundle(raw_payload, source_path=raw_bundle_path)
    canonical_path = store.save_normalized_json(
        build_id=args.build_id,
        filename="canonical.json",
        payload=canonical_document.model_dump(mode="json"),
    )
    return build_canonical_summary(canonical_document, canonical_path)


def main() -> int:
    args = _build_parser().parse_args()
    try:
        summary = asyncio.run(_run_from_args(args))
    except FileNotFoundError:
        print(f"Normalization failed: raw bundle not found for build_id={args.build_id}.")
        return 2
    except json.JSONDecodeError:
        print(f"Normalization failed: raw bundle is invalid JSON for build_id={args.build_id}.")
        return 3
    except ValueError as exc:
        print(f"Normalization failed: {exc}")
        return 4

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
