"""Tests for Azure DevOps token provider."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from azure.core.credentials import AccessToken
from backend.app.services.auth.ado_token_provider import AzureDevOpsTokenProvider
from backend.app.utils.config import Settings
from backend.app.utils.constants import ADO_RESOURCE_SCOPE


class DummyCredential:
    """Simple mock credential with deterministic token output."""

    def __init__(self) -> None:
        self.requested_scopes: list[str] = []

    def get_token(
        self,
        *scopes: str,
        claims: str | None = None,
        tenant_id: str | None = None,
        enable_cae: bool = False,
        **kwargs: Any,
    ) -> AccessToken:
        _ = (claims, tenant_id, enable_cae, kwargs)
        self.requested_scopes.extend(scopes)
        return AccessToken(token="mock-token", expires_on=int(time.time()) + 3600)


def test_token_provider_returns_sync_header_shape() -> None:
    """Sync header helper should return bearer token + json accept headers."""

    credential = DummyCredential()
    settings = Settings(ADO_ORGANIZATION="org", ADO_PROJECT="project")
    provider = AzureDevOpsTokenProvider(settings=settings, credential=credential)

    headers = provider.get_auth_headers_sync()

    assert headers["Authorization"] == "Bearer mock-token"
    assert headers["Accept"] == "application/json"
    assert credential.requested_scopes == [ADO_RESOURCE_SCOPE]


def test_token_provider_returns_async_header_shape() -> None:
    """Async header helper should return same safe header shape."""

    credential = DummyCredential()
    settings = Settings(ADO_ORGANIZATION="org", ADO_PROJECT="project")
    provider = AzureDevOpsTokenProvider(settings=settings, credential=credential)

    headers = asyncio.run(provider.get_auth_headers())

    assert headers["Authorization"] == "Bearer mock-token"
    assert headers["Accept"] == "application/json"

