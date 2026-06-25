"""Tests for the Azure credential smoke script."""

from __future__ import annotations

from typing import Any

from scripts import smoke_azure_credentials


def test_smoke_azure_credentials_help_works_without_azure_access(capsys: Any) -> None:
    try:
        smoke_azure_credentials.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "Validate Azure credential configuration" in capsys.readouterr().out


def test_smoke_azure_credentials_default_does_not_call_network(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    class DummyCredential:
        pass

    monkeypatch.delenv("AZURE_CREDENTIAL_MODE", raising=False)
    monkeypatch.setattr(
        smoke_azure_credentials,
        "get_azure_credential",
        lambda: DummyCredential(),
    )

    assert smoke_azure_credentials.main([]) == 0
    output = capsys.readouterr().out
    assert "Azure credential mode: default" in output
    assert "Credential values and secrets are intentionally not printed." in output
