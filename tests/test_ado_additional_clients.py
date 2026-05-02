"""Tests for additional ADO clients introduced in Phase 2."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from app.clients.ado.base import AzureDevOpsClientConfig
from app.clients.ado.git_client import AzureDevOpsGitClient
from app.clients.ado.test_client import AzureDevOpsTestClient
from app.clients.ado.workitem_client import AzureDevOpsWorkItemClient


class StubTokenProvider:
    async def get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer token", "Accept": "application/json"}

    def get_auth_headers_sync(self) -> dict[str, str]:
        return {"Authorization": "Bearer token", "Accept": "application/json"}


def _config() -> AzureDevOpsClientConfig:
    return AzureDevOpsClientConfig(
        organization="org",
        project="proj",
        api_version="7.1",
        max_retries=0,
    )


def test_work_item_batch_payload() -> None:
    """Work item client should send expected batch body."""

    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(status_code=200, json={"count": 1, "value": []})

    async def run() -> None:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsWorkItemClient(_config(), StubTokenProvider(), http_client)
        try:
            await client.get_work_items_batch([1001, 1002], fields=["System.Id"])
        finally:
            await http_client.aclose()

    asyncio.run(run())
    assert captured["path"].endswith("/_apis/wit/workitemsbatch")
    assert captured["body"] == {"ids": [1001, 1002], "fields": ["System.Id"]}


def test_git_client_can_return_empty_pr_query_payload() -> None:
    """Git PR query may return no linked PRs and should not hard-fail."""

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"queries": [], "results": []})

    async def run() -> dict[str, Any]:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsGitClient(_config(), StubTokenProvider(), http_client)
        try:
            return await client.get_pull_requests_for_commit("repo", "abc")
        finally:
            await http_client.aclose()

    payload = asyncio.run(run())
    assert payload["results"] == []


def test_test_client_paths() -> None:
    """Test client should build expected runs/results paths."""

    paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(status_code=200, json={"value": []})

    async def run() -> None:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsTestClient(_config(), StubTokenProvider(), http_client)
        try:
            await client.get_test_runs(42)
            await client.get_test_results(7, max_results=25)
        finally:
            await http_client.aclose()

    asyncio.run(run())
    assert paths[0].endswith("/_apis/test/runs")
    assert paths[1].endswith("/_apis/test/Runs/7/results")
