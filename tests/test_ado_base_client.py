"""Tests for Azure DevOps base client behavior."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest
from app.clients.ado.base import (
    AzureDevOpsBaseClient,
    AzureDevOpsClientConfig,
    AzureDevOpsClientError,
)


class StubTokenProvider:
    """Stub token provider for client unit tests."""

    async def get_auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer token", "Accept": "application/json"}

    def get_auth_headers_sync(self) -> dict[str, str]:
        return {"Authorization": "Bearer token", "Accept": "application/json"}


def test_base_client_adds_api_version_and_returns_json() -> None:
    """Base client should append api-version and parse JSON object responses."""

    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        return httpx.Response(status_code=200, json={"id": 123, "status": "ok"})

    async def run() -> dict[str, Any]:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsBaseClient(
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
            return await client._get("/_apis/build/builds/123", params={"extra": "value"})
        finally:
            await http_client.aclose()

    payload = asyncio.run(run())

    assert payload["id"] == 123
    assert captured["path"].endswith("/_apis/build/builds/123")
    assert captured["params"]["api-version"] == "7.1"
    assert captured["params"]["extra"] == "value"


def test_base_client_raises_custom_error_for_non_success() -> None:
    """Base client should raise AzureDevOpsClientError for non-success responses."""

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, json={"message": "server exploded"})

    async def run() -> None:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsBaseClient(
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
            await client._get("/_apis/build/builds/123")
        finally:
            await http_client.aclose()

    with pytest.raises(AzureDevOpsClientError) as exc_info:
        asyncio.run(run())

    error = exc_info.value
    assert error.status_code == 500
    assert error.path == "/_apis/build/builds/123"
    assert "server exploded" in error.summary


def test_base_client_post_adds_api_version_and_sends_json_body() -> None:
    """Base client should support POST with api-version and JSON payload."""

    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["params"] = dict(request.url.params)
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(status_code=200, json={"ok": True})

    async def run() -> dict[str, Any]:
        http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AzureDevOpsBaseClient(
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
            return await client._post("/_apis/wit/workitemsbatch", body={"ids": [1, 2]})
        finally:
            await http_client.aclose()

    payload = asyncio.run(run())

    assert payload["ok"] is True
    assert captured["path"].endswith("/_apis/wit/workitemsbatch")
    assert captured["params"]["api-version"] == "7.1"
    assert json.loads(captured["body"]) == {"ids": [1, 2]}
