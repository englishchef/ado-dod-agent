"""Smoke-check DoD run contract normalization and serialization."""

from __future__ import annotations

from pathlib import Path

try:
    from backend.app.models.dod_contracts import normalize_dod_run_input, serialize_dod_run_output
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.models.dod_contracts import normalize_dod_run_input, serialize_dod_run_output


def main() -> int:
    run_input = normalize_dod_run_input(
        {
            "organization": "ado-org",
            "project": "ado-project",
            "build_id": 123456,
            "correlation_id": "contract-smoke",
            "metadata": {"source": "local-smoke"},
        }
    )
    serialize_dod_run_output(
        {
            "run_id": "dod-run-smoke",
            "build_id": run_input.build_id,
            "status": "completed",
            "service_now_payload": {"change_description": "redacted in normal summaries"},
            "confidence": {"overall": 0.9},
            "artifact_paths": {"run_summary": "data/output/123456/run_summary.json"},
            "warnings": [],
            "errors": [],
        },
        fallback_input=run_input,
    )
    print("dod contract smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
