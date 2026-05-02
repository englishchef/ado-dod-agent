"""Azure DevOps token provider implementations."""

from __future__ import annotations

import asyncio
from typing import Protocol

from azure.core.credentials import TokenCredential

from backend.app.services.auth.credentials import get_azure_credential
from backend.app.utils.config import Settings, get_settings
from backend.app.utils.constants import ADO_RESOURCE_SCOPE
from backend.app.utils.logging import get_logger

logger = get_logger(__name__)


class AdoTokenProvider(Protocol):
    """Contract for components that produce Azure DevOps access tokens."""

    async def get_auth_headers(self) -> dict[str, str]:
        """Return authorization headers for Azure DevOps REST calls."""

    def get_auth_headers_sync(self) -> dict[str, str]:
        """Return authorization headers for synchronous script contexts."""


class AzureDevOpsTokenProvider:
    """Token provider backed by Azure Identity for Entra-authenticated ADO calls."""

    settings: Settings
    credential: TokenCredential
    scope: str = ADO_RESOURCE_SCOPE

    def __init__(
        self,
        settings: Settings | None = None,
        credential: TokenCredential | None = None,
        scope: str = ADO_RESOURCE_SCOPE,
    ) -> None:
        resolved_settings = settings or get_settings()
        self.settings = resolved_settings
        self.credential = credential or get_azure_credential(resolved_settings)
        self.scope = scope
        logger.info("ado_token_provider_initialized scope=%s", self.scope)

    def get_auth_headers_sync(self) -> dict[str, str]:
        """Return bearer-token headers for synchronous call sites."""

        token = self.credential.get_token(self.scope)
        return {
            "Authorization": f"Bearer {token.token}",
            "Accept": "application/json",
        }

    async def get_auth_headers(self) -> dict[str, str]:
        """Return bearer-token headers for asynchronous call sites."""

        return await asyncio.to_thread(self.get_auth_headers_sync)


class AzureIdentityAdoTokenProvider(AzureDevOpsTokenProvider):
    """Backward-compatible alias for historical class naming."""

    pass

