"""CLI entrypoint for Phase-2 raw metadata collection."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.collectors.raw_metadata import collect_raw_metadata
from app.core.config import get_settings
from app.models.inputs import CollectRawInput
from pydantic import ValidationError


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect raw Azure DevOps metadata.")
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--organization", type=str, default=None)
    parser.add_argument("--project", type=str, default=None)
    parser.add_argument("--include-tests", type=_parse_bool, default=True)
    parser.add_argument("--include-pull-requests", type=_parse_bool, default=True)
    parser.add_argument("--include-artifacts", type=_parse_bool, default=True)
    parser.add_argument("--max-test-results-per-run", type=int, default=200)
    return parser


def format_result_summary(result: dict[str, Any]) -> str:
    """Render a compact summary without raw payload dumps."""

    summary = result.get("summary", {})
    artifact_paths = result.get("artifact_paths", {})
    collector_errors = result.get("errors", [])
    lines = [
        "Raw metadata collection summary",
        f"- collection_run_id: {result.get('collection_run_id')}",
        f"- status: {result.get('status')}",
        f"- build_id: {result.get('build_id')}",
        f"- pipeline_name: {result.get('pipeline_name')}",
        f"- branch: {result.get('branch')}",
        f"- build_status: {result.get('build_status')}",
        f"- build_result: {result.get('build_result')}",
        f"- timeline_record_count: {summary.get('timeline_record_count', 0)}",
        f"- artifact_count: {summary.get('artifact_count', 0)}",
        f"- work_item_ref_count: {summary.get('work_item_ref_count', 0)}",
        f"- work_item_count: {summary.get('work_item_count', 0)}",
        f"- change_count: {summary.get('change_count', 0)}",
        f"- pull_request_count: {summary.get('pull_request_count', 0)}",
        f"- test_run_count: {summary.get('test_run_count', 0)}",
        f"- test_result_count: {summary.get('test_result_count', 0)}",
        f"- raw_bundle_path: {artifact_paths.get('raw_bundle')}",
    ]
    if collector_errors:
        lines.append("- partial_errors:")
        for error in collector_errors:
            collector = error.get("collector")
            message = error.get("message")
            lines.append(f"  - {collector}: {message}")
    return "\n".join(lines)


async def _run_from_args(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    request = CollectRawInput(
        organization=args.organization or settings.ADO_ORGANIZATION or "",
        project=args.project or settings.ADO_PROJECT or "",
        build_id=args.build_id,
        include_tests=args.include_tests,
        include_pull_requests=args.include_pull_requests,
        include_artifacts=args.include_artifacts,
        max_test_results_per_run=args.max_test_results_per_run,
    )
    result = await collect_raw_metadata(request)
    return result.model_dump(mode="json")


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = asyncio.run(_run_from_args(args))
    except ValidationError as exc:
        print(f"Collection input validation failed: {exc}")
        return 2
    except ValueError as exc:
        print(f"Collection setup failed: {exc}")
        return 3

    print(format_result_summary(result))
    return 0 if result.get("status") in {"completed", "partial"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
