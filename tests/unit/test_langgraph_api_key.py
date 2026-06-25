"""Tests for LangGraph API key Key Vault helper."""

from __future__ import annotations

from typing import Any

import pytest
from backend.app.core import langgraph_api_key
from backend.app.core.langgraph_api_key import (
    LANGGRAPH_KEY_VAULT_SECRET_NAME,
    LANGGRAPH_KEY_VAULT_URL,
    LangGraphApiKeyConfigError,
    get_langgraph_api_key,
    get_redacted_langgraph_api_key_summary,
    validate_langgraph_api_key_config,
)


class FakeSecret:
    def __init__(self, value: str) -> None:
        self.value = value


def test_neither_langgraph_key_vault_var_returns_none_non_strict() -> None:
    assert get_langgraph_api_key(environ={}) is None


def test_one_langgraph_key_vault_var_missing_fails_strict() -> None:
    with pytest.raises(LangGraphApiKeyConfigError, match="Both LANGGRAPH_KEY_VAULT_URL"):
        get_langgraph_api_key(strict=True, environ={LANGGRAPH_KEY_VAULT_URL: "https://vault"})


def test_both_langgraph_key_vault_vars_call_key_vault_client() -> None:
    calls: dict[str, Any] = {}
    credential = object()

    class FakeSecretClient:
        def __init__(self, *, vault_url: str, credential: object) -> None:
            calls["vault_url"] = vault_url
            calls["credential"] = credential

        def get_secret(self, name: str) -> FakeSecret:
            calls["secret_name"] = name
            return FakeSecret("langgraph-api-key-value")

    api_key = get_langgraph_api_key(
        environ={
            LANGGRAPH_KEY_VAULT_URL: "https://vault.example/",
            LANGGRAPH_KEY_VAULT_SECRET_NAME: "langgraph-api-key",
        },
        credential_factory=lambda _: credential,
        secret_client_factory=FakeSecretClient,
    )

    assert api_key == "langgraph-api-key-value"
    assert calls == {
        "vault_url": "https://vault.example/",
        "credential": credential,
        "secret_name": "langgraph-api-key",
    }


def test_langgraph_api_key_helper_uses_central_credential_factory(monkeypatch: Any) -> None:
    calls: dict[str, Any] = {}
    credential = object()

    class FakeSecretClient:
        def __init__(self, *, vault_url: str, credential: object) -> None:
            calls["credential"] = credential

        def get_secret(self, name: str) -> FakeSecret:
            return FakeSecret("langgraph-api-key-value")

    def fake_get_azure_credential(environ: dict[str, str]) -> object:
        calls["environ"] = dict(environ)
        return credential

    monkeypatch.setattr(langgraph_api_key, "get_azure_credential", fake_get_azure_credential)

    assert get_langgraph_api_key(
        environ={
            LANGGRAPH_KEY_VAULT_URL: "https://vault.example/",
            LANGGRAPH_KEY_VAULT_SECRET_NAME: "langgraph-api-key",
        },
        secret_client_factory=FakeSecretClient,
    )

    assert calls["credential"] is credential
    assert calls["environ"][LANGGRAPH_KEY_VAULT_SECRET_NAME] == "langgraph-api-key"


def test_redacted_summary_never_includes_api_key_value() -> None:
    summary = get_redacted_langgraph_api_key_summary(
        {
            LANGGRAPH_KEY_VAULT_URL: "https://vault.example/",
            LANGGRAPH_KEY_VAULT_SECRET_NAME: "langgraph-api-key",
        }
    )

    rendered = str(summary)
    assert "actual-secret" not in rendered
    assert summary["api_key_value_printed"] is False


def test_validate_langgraph_assistant_id_dod() -> None:
    assert validate_langgraph_api_key_config(environ={"LANGGRAPH_ASSISTANT_ID": "dod"}) == []
    assert validate_langgraph_api_key_config(environ={"LANGGRAPH_ASSISTANT_ID": "other"})
