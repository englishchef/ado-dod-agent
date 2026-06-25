"""Credential factory abstractions for Azure authentication."""

from __future__ import annotations

from typing import Any

from backend.app.core.azure_credentials import get_azure_credential as _get_azure_credential
from backend.app.core.azure_credentials import get_redacted_credential_summary
from backend.app.utils.config import Settings, get_settings
from backend.app.utils.logging import get_logger

logger = get_logger(__name__)


def get_azure_credential(settings: Settings | None = None) -> Any:
    """Return the centralized Azure credential for local dev and Azure runtime hosts."""

    resolved_settings = settings or get_settings()
    environ = {
        "AZURE_CREDENTIAL_MODE": resolved_settings.AZURE_CREDENTIAL_MODE,
        "AZURE_CLIENT_ID": resolved_settings.AZURE_CLIENT_ID or "",
        "AZURE_USER_ASSIGNED_CLIENT_ID": resolved_settings.AZURE_USER_ASSIGNED_CLIENT_ID or "",
        "AZURE_TENANT_ID": resolved_settings.AZURE_TENANT_ID or "",
        "AZURE_CLIENT_SECRET": resolved_settings.AZURE_CLIENT_SECRET or "",
    }
    summary = get_redacted_credential_summary(environ)
    logger.info(
        "auth_init mode=%s app_env=%s has_client_id=%s has_tenant_id=%s "
        "has_client_secret=%s has_user_assigned_client_id_alias=%s",
        summary.mode,
        resolved_settings.APP_ENV,
        summary.client_id_configured,
        summary.tenant_id_configured,
        summary.client_secret_configured,
        summary.user_assigned_client_id_alias_configured,
    )
    return _get_azure_credential(environ)


def build_azure_credential(settings: Settings | None = None) -> Any:
    """Backward-compatible alias for `get_azure_credential`."""

    return get_azure_credential(settings)

