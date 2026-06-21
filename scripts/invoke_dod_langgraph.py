"""Invoke the deployed LangGraph DoD assistant with structured input."""

from __future__ import annotations

import argparse
import asyncio
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

try:
    from backend.app.models.dod_contracts import normalize_dod_run_input
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.models.dod_contracts import normalize_dod_run_input

ASSISTANT_NAME = "dod"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Invoke the LangGraph DoD assistant.")
    parser.add_argument("--organization", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--mode", default="pipeline")
    parser.add_argument("--correlation-id", default=None)
    return parser


def build_structured_input(args: argparse.Namespace) -> dict[str, Any]:
    """Build the structured DoD assistant input from CLI args."""

    return normalize_dod_run_input(
        {
            "organization": args.organization,
            "project": args.project,
            "build_id": args.build_id,
            "mode": args.mode,
            "correlation_id": args.correlation_id,
            "source": "langgraph-sdk-script",
        }
    ).model_dump(mode="json", exclude_none=True)


def format_safe_summary(payload: Mapping[str, Any]) -> str:
    """Render a safe invocation summary without generated payload text or secrets."""

    rule_summary = payload.get("rule_evaluation_summary")
    if not isinstance(rule_summary, dict):
        rule_summary = {}
    artifact_paths = payload.get("artifact_paths")
    artifact_keys = sorted(artifact_paths) if isinstance(artifact_paths, dict) else []
    lines = [
        "DoD LangGraph run summary",
        f"- run_id: {payload.get('run_id') or 'n/a'}",
        f"- build_id: {payload.get('build_id') or 'n/a'}",
        f"- status: {payload.get('status') or 'n/a'}",
        f"- rule_recommended_status: {rule_summary.get('recommended_status') or 'n/a'}",
        f"- artifact_path_keys: {', '.join(artifact_keys) if artifact_keys else 'n/a'}",
    ]
    return "\n".join(lines)


async def invoke_dod_assistant(
    *,
    url: str,
    api_key: str | None,
    input_payload: dict[str, Any],
) -> Mapping[str, Any]:
    """Invoke the `dod` assistant through LangGraph SDK."""

    try:
        from langgraph_sdk import get_client
    except ModuleNotFoundError as exc:
        if exc.name != "langgraph_sdk":
            raise
        raise RuntimeError(
            "langgraph_sdk is not installed. Install the LangGraph SDK in this environment "
            "or run this script where the enterprise SDK dependencies are available."
        ) from exc

    client_kwargs: dict[str, Any] = {"url": url}
    if api_key:
        client_kwargs["api_key"] = api_key
    client = get_client(**client_kwargs)
    thread = await client.threads.create()
    run = await client.runs.create(
        thread["thread_id"],
        ASSISTANT_NAME,
        input=input_payload,
    )
    return run if isinstance(run, Mapping) else {"run_id": getattr(run, "run_id", None)}


def main() -> int:
    args = _build_parser().parse_args()
    url = os.environ.get("DOD_LANGGRAPH_URL")
    if not url:
        print("Error: DOD_LANGGRAPH_URL is required to invoke the LangGraph DoD assistant.")
        return 2

    try:
        input_payload = build_structured_input(args)
        result = asyncio.run(
            invoke_dod_assistant(
                url=url,
                api_key=os.environ.get("LANGSMITH_API_KEY"),
                input_payload=input_payload,
            )
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return 2

    print(format_safe_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
