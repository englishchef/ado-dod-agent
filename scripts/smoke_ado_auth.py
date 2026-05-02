"""Smoke test Azure DevOps Entra auth and basic build API access."""

from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.auth.ado_token_provider import AzureDevOpsTokenProvider
from app.auth.credentials import get_azure_credential
from app.clients.ado.base import AzureDevOpsClientConfig, AzureDevOpsClientError
from app.clients.ado.build_client import AzureDevOpsBuildClient
from app.core.config import get_settings
from app.core.logging import configure_logging


def build_safe_summary(
    build: dict[str, Any],
    timeline: dict[str, Any],
    work_items: dict[str, Any],
    auth_succeeded: bool,
) -> dict[str, Any]:
    """Build a compact, non-sensitive smoke-test summary."""

    definition_raw = build.get("definition")
    definition: dict[str, Any] = definition_raw if isinstance(definition_raw, dict) else {}

    requested_by_raw = build.get("requestedBy")
    requested_by: dict[str, Any] = requested_by_raw if isinstance(requested_by_raw, dict) else {}

    timeline_records_raw = timeline.get("records")
    timeline_records: list[Any] = (
        timeline_records_raw if isinstance(timeline_records_raw, list) else []
    )

    linked_work_items_raw = work_items.get("value")
    linked_work_items: list[Any] = (
        linked_work_items_raw if isinstance(linked_work_items_raw, list) else []
    )

    return {
        "authentication_succeeded": auth_succeeded,
        "build_id": build.get("id"),
        "pipeline_name": definition.get("name"),
        "branch": build.get("sourceBranch"),
        "source_version": build.get("sourceVersion"),
        "status": build.get("status"),
        "result": build.get("result"),
        "requested_by": requested_by.get("displayName"),
        "timeline_record_count": len(timeline_records),
        "linked_work_item_ref_count": len(linked_work_items),
    }


def format_summary(summary: dict[str, Any]) -> str:
    """Render summary values for CLI output."""

    lines = ["Azure DevOps smoke validation summary"]
    for key in (
        "authentication_succeeded",
        "build_id",
        "pipeline_name",
        "branch",
        "source_version",
        "status",
        "result",
        "requested_by",
        "timeline_record_count",
        "linked_work_item_ref_count",
    ):
        lines.append(f"- {key}: {summary.get(key)}")
    return "\n".join(lines)


async def run_smoke(build_id: int, include_work_items: bool) -> dict[str, Any]:
    """Execute smoke calls against Azure DevOps Build APIs."""

    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    if not settings.ADO_ORGANIZATION or not settings.ADO_PROJECT:
        raise ValueError("ADO_ORGANIZATION and ADO_PROJECT must be set.")

    credential = get_azure_credential(settings)
    token_provider = AzureDevOpsTokenProvider(settings=settings, credential=credential)
    auth_headers = await token_provider.get_auth_headers()
    auth_succeeded = "Authorization" in auth_headers and auth_headers["Authorization"].startswith(
        "Bearer "
    )

    client = AzureDevOpsBuildClient(
        config=AzureDevOpsClientConfig.from_settings(settings),
        token_provider=token_provider,
    )
    try:
        build = await client.get_build(build_id)
        timeline = await client.get_build_timeline(build_id)
        work_items = (
            await client.get_build_work_items_refs(build_id)
            if include_work_items
            else {"value": []}
        )
    finally:
        await client.aclose()

    return build_safe_summary(
        build=build,
        timeline=timeline,
        work_items=work_items,
        auth_succeeded=auth_succeeded,
    )


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Azure DevOps auth and build API smoke test.")
    parser.add_argument("--build-id", type=int, required=True, help="Azure DevOps build id.")
    parser.add_argument(
        "--skip-work-items",
        action="store_true",
        help="Skip linked work-item reference request.",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""

    args = _build_argument_parser().parse_args()
    try:
        summary = asyncio.run(
            run_smoke(build_id=args.build_id, include_work_items=not args.skip_work_items)
        )
    except ValueError as exc:
        print(f"Smoke validation failed: {exc}")
        return 2
    except AzureDevOpsClientError as exc:
        if exc.status_code == 404:
            print(
                "Smoke validation failed: build not found. "
                f"build_id={args.build_id} path={exc.path}"
            )
            return 3
        print(
            "Smoke validation failed: Azure DevOps API request failed. "
            f"status_code={exc.status_code} path={exc.path} summary={exc.summary}"
        )
        return 4

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
