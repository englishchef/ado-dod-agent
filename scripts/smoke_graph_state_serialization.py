"""Offline smoke validation for compact LangGraph checkpoint state."""

from __future__ import annotations

from pathlib import Path

try:
    from backend.app.utils.config import get_settings
    from backend.app.utils.state_serialization import (
        GraphStateValidationError,
        validate_graph_state,
    )
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.utils.config import get_settings
    from backend.app.utils.state_serialization import (
        GraphStateValidationError,
        validate_graph_state,
    )


def representative_graph_state() -> dict[str, object]:
    """Return a safe representative state without reading external systems."""

    return {
        "organization": "ado-org",
        "project": "ado-project",
        "build_id": 123456,
        "mode": "pipeline",
        "correlation_id": "graph-state-smoke",
        "run_id": "dod-run-smoke-123456",
        "status": "started",
        "current_phase": "evidence",
        "artifact_paths": {
            "raw_bundle": "cosmos://dod-run-smoke-123456/raw_bundle",
            "canonical": "cosmos://dod-run-smoke-123456/canonical",
            "evidence_bundle": "cosmos://dod-run-smoke-123456/evidence_bundle",
            "bucket_3_rollback_risk": (
                "cosmos://dod-run-smoke-123456/bucket_3_rollback_risk"
            ),
        },
        "bucket_3_summary": {
            "selected_environment": "UAT",
            "selected_stage_name": "UAT",
            "estimated_backout_minutes": 90,
            "normalized_actions": ["solution_upgrade", "solution_deployment"],
            "fallback_used": False,
            "recursive_traversal_used": True,
            "descendant_count": 12,
            "max_depth": 3,
        },
        "warnings": [],
        "errors": [],
        "service_now_payload": None,
        "confidence": None,
        "rule_evaluation_summary": None,
    }


def main() -> int:
    settings = get_settings()
    try:
        diagnostics = validate_graph_state(
            representative_graph_state(),
            context="graph_state_smoke",
            warn_bytes=int(settings.DOD_GRAPH_STATE_WARN_BYTES),
            max_bytes=int(settings.DOD_GRAPH_STATE_MAX_BYTES),
        )
    except GraphStateValidationError as exc:
        print(f"graph state serialization failed: {exc.code}")
        return 1

    print(f"graph state size bytes: {diagnostics['state_size_bytes']}")
    print("largest graph state keys:")
    for item in diagnostics["largest_keys"]:
        print(
            f"  {item['key']}: size_bytes={item['size_bytes']} type={item['type']}"
        )
    if diagnostics.get("warning_required"):
        print("graph state serialization passed with size warning")
    else:
        print("graph state serialization passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
