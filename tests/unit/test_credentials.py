"""Tests for Azure credential factory."""

from __future__ import annotations

from backend.app.services.auth import credentials as credentials_module
from backend.app.utils.config import Settings
from pytest import MonkeyPatch


def test_get_azure_credential_initializes_default_credential(
    monkeypatch: MonkeyPatch,
) -> None:
    """Legacy auth helper should delegate to the centralized credential factory."""

    class DummyCredential:
        pass

    captured_environ: dict[str, str] = {}

    def fake_core_credential(environ: dict[str, str]) -> DummyCredential:
        captured_environ.update(environ)
        return DummyCredential()

    monkeypatch.setattr(credentials_module, "_get_azure_credential", fake_core_credential)

    settings = Settings(
        APP_ENV="local",
        AZURE_CREDENTIAL_MODE="managed_identity",
        AZURE_CLIENT_ID="managed-identity-client-id",
    )
    credential = credentials_module.get_azure_credential(settings)

    assert isinstance(credential, DummyCredential)
    assert captured_environ["AZURE_CREDENTIAL_MODE"] == "managed_identity"
    assert captured_environ["AZURE_CLIENT_ID"] == "managed-identity-client-id"

