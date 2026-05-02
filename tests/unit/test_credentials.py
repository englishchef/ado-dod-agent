"""Tests for Azure credential factory."""

from __future__ import annotations

from backend.app.services.auth import credentials as credentials_module
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def test_get_azure_credential_initializes_default_credential(
    monkeypatch: MonkeyPatch,
) -> None:
    """Credential factory should initialize DefaultAzureCredential without live calls."""

    captured_kwargs: dict[str, object] = {}

    class DummyCredential:
        pass

    def fake_default_credential(**kwargs: object) -> DummyCredential:
        captured_kwargs.update(kwargs)
        return DummyCredential()

    monkeypatch.setattr(credentials_module, "DefaultAzureCredential", fake_default_credential)

    settings = Settings(APP_ENV="local", AZURE_CLIENT_ID="managed-identity-client-id")
    credential = credentials_module.get_azure_credential(settings)

    assert isinstance(credential, DummyCredential)
    assert captured_kwargs["managed_identity_client_id"] == "managed-identity-client-id"
    assert captured_kwargs["exclude_interactive_browser_credential"] is False

