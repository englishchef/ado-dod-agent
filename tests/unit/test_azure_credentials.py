"""Tests for the centralized Azure credential factory."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from backend.app.core.azure_credentials import (
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_CREDENTIAL_MODE,
    AZURE_TENANT_ID,
    AZURE_USER_ASSIGNED_CLIENT_ID,
    AzureCredentialConfigError,
    get_azure_credential,
    get_redacted_credential_summary,
    validate_azure_credential_config,
)


class FakeDefaultAzureCredential:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeManagedIdentityCredential:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeClientSecretCredential:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def _install_fake_azure_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_azure = types.ModuleType("azure")
    fake_identity = types.ModuleType("azure.identity")
    fake_identity.DefaultAzureCredential = FakeDefaultAzureCredential
    fake_identity.ManagedIdentityCredential = FakeManagedIdentityCredential
    fake_identity.ClientSecretCredential = FakeClientSecretCredential
    monkeypatch.setitem(sys.modules, "azure", fake_azure)
    monkeypatch.setitem(sys.modules, "azure.identity", fake_identity)


def test_default_mode_creates_default_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_azure_identity(monkeypatch)

    credential = get_azure_credential({})

    assert isinstance(credential, FakeDefaultAzureCredential)
    assert credential.kwargs == {}


def test_managed_identity_mode_creates_managed_identity_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_azure_identity(monkeypatch)

    credential = get_azure_credential({AZURE_CREDENTIAL_MODE: "managed_identity"})

    assert isinstance(credential, FakeManagedIdentityCredential)
    assert credential.kwargs == {}


def test_managed_identity_mode_with_client_id_passes_client_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_azure_identity(monkeypatch)

    credential = get_azure_credential(
        {AZURE_CREDENTIAL_MODE: "managed_identity", AZURE_CLIENT_ID: "mi-client-id"}
    )

    assert credential.kwargs == {"client_id": "mi-client-id"}


def test_managed_identity_alias_and_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_azure_identity(monkeypatch)

    alias_credential = get_azure_credential(
        {
            AZURE_CREDENTIAL_MODE: "managed_identity",
            AZURE_USER_ASSIGNED_CLIENT_ID: "alias-client-id",
        }
    )
    precedence_credential = get_azure_credential(
        {
            AZURE_CREDENTIAL_MODE: "managed_identity",
            AZURE_CLIENT_ID: "canonical-client-id",
            AZURE_USER_ASSIGNED_CLIENT_ID: "alias-client-id",
        }
    )

    assert alias_credential.kwargs == {"client_id": "alias-client-id"}
    assert precedence_credential.kwargs == {"client_id": "canonical-client-id"}


def test_client_secret_mode_requires_all_fields() -> None:
    assert validate_azure_credential_config({AZURE_CREDENTIAL_MODE: "client_secret"}) == [
        "AZURE_CLIENT_ID is required when AZURE_CREDENTIAL_MODE=client_secret.",
        "AZURE_TENANT_ID is required when AZURE_CREDENTIAL_MODE=client_secret.",
        "AZURE_CLIENT_SECRET is required when AZURE_CREDENTIAL_MODE=client_secret.",
    ]


def test_client_secret_mode_creates_client_secret_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_azure_identity(monkeypatch)

    credential = get_azure_credential(
        {
            AZURE_CREDENTIAL_MODE: "client_secret",
            AZURE_CLIENT_ID: "client-id",
            AZURE_TENANT_ID: "tenant-id",
            AZURE_CLIENT_SECRET: "secret-value",
        }
    )

    assert isinstance(credential, FakeClientSecretCredential)
    assert credential.kwargs == {
        "tenant_id": "tenant-id",
        "client_id": "client-id",
        "client_secret": "secret-value",
    }


def test_invalid_credential_mode_fails_clearly() -> None:
    with pytest.raises(AzureCredentialConfigError, match="AZURE_CREDENTIAL_MODE"):
        get_azure_credential({AZURE_CREDENTIAL_MODE: "unsupported"})


def test_redacted_summary_never_includes_secret_values() -> None:
    summary = get_redacted_credential_summary(
        {
            AZURE_CREDENTIAL_MODE: "client_secret",
            AZURE_CLIENT_ID: "client-id",
            AZURE_TENANT_ID: "tenant-id",
            AZURE_CLIENT_SECRET: "secret-value",
        }
    )

    rendered = "\n".join(summary.lines())
    assert "secret-value" not in rendered
    assert "client-id" not in rendered
    assert "tenant-id" not in rendered
    assert "Client secret configured: yes" in rendered
