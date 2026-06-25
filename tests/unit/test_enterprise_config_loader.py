"""Tests for enterprise Key Vault config loading."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest
from backend.app.core import enterprise_config
from backend.app.core.enterprise_config import (
    AGENT_CONFIG_KEY_VAULT_URL,
    AGENT_CONFIG_SECRET_NAME,
    AZURE_USER_ASSIGNED_CLIENT_ID,
    EnterpriseConfigError,
    create_default_azure_credential,
    load_agent_config_from_key_vault,
    parse_agent_config_json,
)


class FakeSecret:
    def __init__(self, value: str) -> None:
        self.value = value


def test_no_agent_config_pointer_returns_empty_config() -> None:
    assert load_agent_config_from_key_vault(environ={}) == {}


def test_both_agent_config_pointers_call_key_vault_client() -> None:
    calls: dict[str, Any] = {}

    class FakeSecretClient:
        def __init__(self, *, vault_url: str, credential: object) -> None:
            calls["vault_url"] = vault_url
            calls["credential"] = credential

        def get_secret(self, name: str) -> FakeSecret:
            calls["secret_name"] = name
            return FakeSecret('{"DOD_STORAGE_BACKEND": "cosmos"}')

    credential = object()
    config = load_agent_config_from_key_vault(
        environ={
            AGENT_CONFIG_KEY_VAULT_URL: "https://vault.example/",
            AGENT_CONFIG_SECRET_NAME: "dod-config",
        },
        credential_factory=lambda _: credential,
        secret_client_factory=FakeSecretClient,
    )

    assert config == {"DOD_STORAGE_BACKEND": "cosmos"}
    assert calls == {
        "vault_url": "https://vault.example/",
        "credential": credential,
        "secret_name": "dod-config",
    }


def test_key_vault_loader_uses_central_credential_factory(monkeypatch: Any) -> None:
    calls: dict[str, Any] = {}
    credential = object()

    class FakeSecretClient:
        def __init__(self, *, vault_url: str, credential: object) -> None:
            calls["vault_url"] = vault_url
            calls["credential"] = credential

        def get_secret(self, name: str) -> FakeSecret:
            calls["secret_name"] = name
            return FakeSecret('{"DOD_STORAGE_BACKEND": "cosmos"}')

    def fake_get_azure_credential(environ: dict[str, str]) -> object:
        calls["credential_environ"] = dict(environ)
        return credential

    monkeypatch.setattr(enterprise_config, "get_azure_credential", fake_get_azure_credential)

    config = load_agent_config_from_key_vault(
        environ={
            AGENT_CONFIG_KEY_VAULT_URL: "https://vault.example/",
            AGENT_CONFIG_SECRET_NAME: "dod-config",
            "AZURE_CREDENTIAL_MODE": "client_secret",
        },
        secret_client_factory=FakeSecretClient,
    )

    assert config == {"DOD_STORAGE_BACKEND": "cosmos"}
    assert calls["credential"] is credential
    assert calls["credential_environ"]["AZURE_CREDENTIAL_MODE"] == "client_secret"


def test_one_agent_config_pointer_missing_fails_in_strict_mode() -> None:
    with pytest.raises(EnterpriseConfigError, match="Both AGENT_CONFIG_KEY_VAULT_URL"):
        load_agent_config_from_key_vault(
            strict=True,
            environ={AGENT_CONFIG_KEY_VAULT_URL: "https://vault.example/"},
        )


def test_invalid_json_secret_fails_clearly() -> None:
    with pytest.raises(EnterpriseConfigError, match="valid JSON"):
        parse_agent_config_json("{not-json")


def test_non_object_json_secret_fails_clearly() -> None:
    with pytest.raises(EnterpriseConfigError, match="JSON object"):
        parse_agent_config_json('["not", "object"]')


def test_user_assigned_identity_client_id_is_passed_to_credential(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    class FakeDefaultAzureCredential:
        def __init__(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    fake_azure = types.ModuleType("azure")
    fake_identity = types.ModuleType("azure.identity")
    fake_identity.DefaultAzureCredential = FakeDefaultAzureCredential
    monkeypatch.setitem(sys.modules, "azure", fake_azure)
    monkeypatch.setitem(sys.modules, "azure.identity", fake_identity)

    credential = create_default_azure_credential(
        {AZURE_USER_ASSIGNED_CLIENT_ID: "user-assigned-client-id"}
    )

    assert isinstance(credential, FakeDefaultAzureCredential)
    assert calls == [{"managed_identity_client_id": "user-assigned-client-id"}]


def test_missing_user_assigned_client_id_uses_default_credential_path(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []

    class FakeDefaultAzureCredential:
        def __init__(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    fake_azure = types.ModuleType("azure")
    fake_identity = types.ModuleType("azure.identity")
    fake_identity.DefaultAzureCredential = FakeDefaultAzureCredential
    monkeypatch.setitem(sys.modules, "azure", fake_azure)
    monkeypatch.setitem(sys.modules, "azure.identity", fake_identity)

    credential = create_default_azure_credential({})

    assert isinstance(credential, FakeDefaultAzureCredential)
    assert calls == [{}]


def test_key_vault_loader_does_not_print_secret_values(capsys: Any) -> None:
    class FakeSecretClient:
        def __init__(self, *, vault_url: str, credential: object) -> None:
            self.vault_url = vault_url
            self.credential = credential

        def get_secret(self, name: str) -> FakeSecret:
            return FakeSecret('{"COSMOS_KEY": "secret-value-should-not-print"}')

    load_agent_config_from_key_vault(
        environ={
            AGENT_CONFIG_KEY_VAULT_URL: "https://vault.example/",
            AGENT_CONFIG_SECRET_NAME: "dod-config",
        },
        credential_factory=lambda _: object(),
        secret_client_factory=FakeSecretClient,
    )

    captured = capsys.readouterr()
    assert "secret-value-should-not-print" not in captured.out
    assert "secret-value-should-not-print" not in captured.err
