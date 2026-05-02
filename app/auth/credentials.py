"""Credential factory abstractions for Azure authentication."""

from __future__ import annotations

from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential
from backend.app.utils.config import Settings, get_settings
from backend.app.utils.logging import get_logger

logger = get_logger(__name__)


def get_azure_credential(settings: Settings | None = None) -> TokenCredential:
    """Return a `DefaultAzureCredential` for local dev and Azure runtime hosts."""

    resolved_settings = settings or get_settings()
    logger.info(
        "auth_init provider=DefaultAzureCredential app_env=%s has_client_id=%s has_tenant_id=%s",
        resolved_settings.APP_ENV,
        bool(resolved_settings.AZURE_CLIENT_ID),
        bool(resolved_settings.AZURE_TENANT_ID),
    )
    credential = DefaultAzureCredential(
        managed_identity_client_id=resolved_settings.AZURE_CLIENT_ID,
        exclude_interactive_browser_credential=resolved_settings.APP_ENV.lower() == "prod",
    )
    logger.info(
        "auth_chain_ready supports=environment,managed_identity,azure_cli,"
        "developer_cli,shared_token_cache"
    )
    return credential


def build_azure_credential(settings: Settings | None = None) -> TokenCredential:
    """Backward-compatible alias for `get_azure_credential`."""

    return get_azure_credential(settings)

