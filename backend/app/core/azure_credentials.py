"""Central Azure credential factory for DoD runtime integrations."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

AZURE_CREDENTIAL_MODE = "AZURE_CREDENTIAL_MODE"
AZURE_CREDENTIAL_MODE_MANAGED_IDENTITY = "managed_identity"
AZURE_CREDENTIAL_MODE_CLIENT_SECRET = "client_secret"
AZURE_CREDENTIAL_MODE_DEFAULT = "default"
VALID_AZURE_CREDENTIAL_MODES = {
    AZURE_CREDENTIAL_MODE_MANAGED_IDENTITY,
    AZURE_CREDENTIAL_MODE_CLIENT_SECRET,
    AZURE_CREDENTIAL_MODE_DEFAULT,
}

AZURE_CLIENT_ID = "AZURE_CLIENT_ID"
AZURE_TENANT_ID = "AZURE_TENANT_ID"
AZURE_CLIENT_SECRET = "AZURE_CLIENT_SECRET"
AZURE_USER_ASSIGNED_CLIENT_ID = "AZURE_USER_ASSIGNED_CLIENT_ID"


class AzureCredentialConfigError(ValueError):
    """Raised when Azure credential configuration is invalid."""


@dataclass(frozen=True)
class RedactedAzureCredentialSummary:
    """Secret-safe Azure credential configuration summary."""

    mode: str
    client_id_configured: bool
    tenant_id_configured: bool
    client_secret_configured: bool
    user_assigned_client_id_alias_configured: bool

    def lines(self) -> list[str]:
        """Return display lines without credential values."""

        return [
            f"Azure credential mode: {self.mode}",
            f"Client ID configured: {_yes_no(self.client_id_configured)}",
            f"Tenant ID configured: {_yes_no(self.tenant_id_configured)}",
            f"Client secret configured: {_yes_no(self.client_secret_configured)}",
            "User-assigned client ID alias configured: "
            f"{_yes_no(self.user_assigned_client_id_alias_configured)}",
        ]


def get_azure_credential(environ: Mapping[str, str] | None = None) -> Any:
    """Return the configured Azure SDK credential without logging secret values."""

    env = os.environ if environ is None else environ
    mode = get_azure_credential_mode(env)
    errors = validate_azure_credential_config(env)
    if errors:
        raise AzureCredentialConfigError("; ".join(errors))

    if mode == AZURE_CREDENTIAL_MODE_MANAGED_IDENTITY:
        from azure.identity import ManagedIdentityCredential

        client_id = _managed_identity_client_id(env)
        if client_id:
            return ManagedIdentityCredential(client_id=client_id)
        return ManagedIdentityCredential()

    if mode == AZURE_CREDENTIAL_MODE_CLIENT_SECRET:
        from azure.identity import ClientSecretCredential

        return ClientSecretCredential(
            tenant_id=str(env[AZURE_TENANT_ID]),
            client_id=str(env[AZURE_CLIENT_ID]),
            client_secret=str(env[AZURE_CLIENT_SECRET]),
        )

    from azure.identity import DefaultAzureCredential

    client_id = _managed_identity_client_id(env)
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


def get_azure_credential_mode(environ: Mapping[str, str] | None = None) -> str:
    """Return configured Azure credential mode, defaulting to local-compatible default."""

    env = os.environ if environ is None else environ
    mode = str(env.get(AZURE_CREDENTIAL_MODE) or AZURE_CREDENTIAL_MODE_DEFAULT).strip().lower()
    if mode not in VALID_AZURE_CREDENTIAL_MODES:
        raise AzureCredentialConfigError(
            "AZURE_CREDENTIAL_MODE must be one of: client_secret, default, managed_identity."
        )
    return mode


def validate_azure_credential_config(environ: Mapping[str, str] | None = None) -> list[str]:
    """Validate credential config without creating a credential or printing values."""

    env = os.environ if environ is None else environ
    try:
        mode = get_azure_credential_mode(env)
    except AzureCredentialConfigError as exc:
        return [str(exc)]

    if mode != AZURE_CREDENTIAL_MODE_CLIENT_SECRET:
        return []

    missing = [
        name
        for name in (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
        if not _present(env.get(name))
    ]
    return [f"{name} is required when AZURE_CREDENTIAL_MODE=client_secret." for name in missing]


def get_redacted_credential_summary(
    environ: Mapping[str, str] | None = None,
) -> RedactedAzureCredentialSummary:
    """Return a safe credential summary for logs and smoke scripts."""

    env = os.environ if environ is None else environ
    return RedactedAzureCredentialSummary(
        mode=get_azure_credential_mode(env),
        client_id_configured=_present(env.get(AZURE_CLIENT_ID)),
        tenant_id_configured=_present(env.get(AZURE_TENANT_ID)),
        client_secret_configured=_present(env.get(AZURE_CLIENT_SECRET)),
        user_assigned_client_id_alias_configured=_present(
            env.get(AZURE_USER_ASSIGNED_CLIENT_ID)
        ),
    )


def _managed_identity_client_id(env: Mapping[str, str]) -> str | None:
    """Return user-assigned managed identity client id with canonical precedence."""

    return _present_value(env.get(AZURE_CLIENT_ID)) or _present_value(
        env.get(AZURE_USER_ASSIGNED_CLIENT_ID)
    )


def _present(value: Any) -> bool:
    return _present_value(value) is not None


def _present_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
