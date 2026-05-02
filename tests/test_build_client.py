"""Tests for Azure DevOps build client endpoints."""

from __future__ import annotations

import asyncio

import httpx
from app.clients.ado.base import AzureDevOpsClientConfig
from app.clients.ado.build_client import AzureDevOpsBuildClient


class StubTokenProvider:
    """Stub token provider for build-client tests."""

    async def get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer token", "Accept": "application/json"}

    def get_auth_headers_sync(self) -> dict[str, str]:
        return {"Authorization": "Bearer token", "Accept": "application/json"}


def test_build_client_hits_expected_paths() -> None:
    """Build client methods should call expected build API paths."""

    requested_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(status_code=200, json={"value": []})

    async def run() -> None:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsBuildClient(
            config=AzureDevOpsClientConfig(
                organization="org",
                project="proj",
                api_version="7.1",
                max_retries=0,
            ),
            token_provider=StubTokenProvider(),
            http_client=http_client,
        )
        try:
            await client.get_build(42)
            await client.get_build_timeline(42)
            await client.get_build_work_items_refs(42)
        finally:
            await http_client.aclose()

    asyncio.run(run())

    assert requested_paths[0].endswith("/_apis/build/builds/42")
    assert requested_paths[1].endswith("/_apis/build/builds/42/timeline")
    assert requested_paths[2].endswith("/_apis/build/builds/42/workitems")


def test_build_client_changes_and_artifacts_paths() -> None:
    """Build client should call changes and artifacts endpoints."""

    requested_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        return httpx.Response(status_code=200, json={"value": []})

    async def run() -> None:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsBuildClient(
            config=AzureDevOpsClientConfig(
                organization="org",
                project="proj",
                api_version="7.1",
                max_retries=0,
            ),
            token_provider=StubTokenProvider(),
            http_client=http_client,
        )
        try:
            await client.get_build_changes(42)
            await client.get_build_artifacts(42)
        finally:
            await http_client.aclose()

    asyncio.run(run())

    assert requested_paths[0].endswith("/_apis/build/builds/42/changes")
    assert requested_paths[1].endswith("/_apis/build/builds/42/artifacts")
