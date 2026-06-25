"""Smoke-check DoD LangSmith tracing helpers without requiring LangSmith."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

try:
    from backend.app.services.observability.langsmith_tracing import (
        build_run_metadata,
        trace_event,
    )
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.services.observability.langsmith_tracing import (
        build_run_metadata,
        trace_event,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke-test DoD LangSmith tracing helpers.")
    parser.add_argument("--enabled", action="store_true", help="Attempt one enabled trace event.")
    parser.add_argument(
        "--trace-mode",
        choices=("metadata_only", "summary", "debug_redacted"),
        default=None,
    )
    parser.add_argument("--strict", action="store_true", help="Fail if the enabled trace fails.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.trace_mode:
        os.environ["DOD_TRACE_MODE"] = args.trace_mode

    metadata = build_run_metadata(
        input_data={
            "organization": "ado-org",
            "project": "ado-project",
            "build_id": 123456,
            "correlation_id": "langsmith-smoke",
            "metadata": {"source": "smoke"},
            "authorization": "Bearer should-not-print",
        },
        result={
            "run_id": "dod-run-smoke",
            "build_id": 123456,
            "status": "completed",
            "service_now_payload": {"change_description": "should-not-print"},
            "confidence": {"overall": 0.9},
            "artifact_paths": {"run_summary": "summary.json"},
        },
        timings={"duration_ms": 25, "phase_durations_ms": {"input_normalization": 1}},
        storage_backend="local_json",
    )
    rendered = str(metadata)
    if "should-not-print" in rendered:
        print("Error: unsafe value appeared in trace metadata.")
        return 2

    previous = os.environ.get("LANGSMITH_TRACING")
    os.environ["LANGSMITH_TRACING"] = "false"
    trace_event("dod smoke disabled", metadata)
    if previous is None:
        os.environ.pop("LANGSMITH_TRACING", None)
    else:
        os.environ["LANGSMITH_TRACING"] = previous

    if not args.enabled:
        print("LangSmith tracing smoke test passed (disabled no-op)")
        return 0

    os.environ["LANGSMITH_TRACING"] = "true"
    submitted = trace_event("dod smoke enabled", metadata)
    if not submitted:
        if args.strict:
            print("Error: LangSmith enabled smoke failed.")
            return 2
        print("LangSmith enabled smoke completed with non-fatal trace failure")
        return 0

    print("LangSmith enabled smoke completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
