"""Tests for the LLM smoke access script."""

from __future__ import annotations

from typing import Any

from backend.app.utils.config import Settings
from pytest import MonkeyPatch
from scripts import smoke_llm_access


def test_smoke_script_returns_success_with_mocked_client(
    monkeypatch: MonkeyPatch,
    capsys: Any,
) -> None:
    settings = Settings(
        AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
        AZURE_OPENAI_DEPLOYMENT="dod-smoke",
        AZURE_OPENAI_API_VERSION="2024-10-21",
        AZURE_OPENAI_AUTH_MODE="entra",
    )

    monkeypatch.setattr(smoke_llm_access, "get_settings", lambda: settings)
    monkeypatch.setattr(smoke_llm_access, "run_smoke", lambda: {"status": "ok"})

    exit_code = smoke_llm_access.main()
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "LLM smoke test succeeded" in output
    assert "Auth mode: entra" in output
    assert "Deployment: dod-smoke" in output
    assert 'Response: {"status": "ok"}' in output


def test_smoke_script_does_not_print_tokens_or_authorization_headers(
    monkeypatch: MonkeyPatch,
    capsys: Any,
) -> None:
    settings = Settings(
        AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/",
        AZURE_OPENAI_DEPLOYMENT="dod-smoke",
        AZURE_OPENAI_API_VERSION="2024-10-21",
        AZURE_OPENAI_AUTH_MODE="entra",
    )

    monkeypatch.setattr(smoke_llm_access, "get_settings", lambda: settings)
    monkeypatch.setattr(smoke_llm_access, "run_smoke", lambda: {"status": "ok"})

    exit_code = smoke_llm_access.main()
    output = capsys.readouterr().out.lower()

    assert exit_code == 0
    assert "token" not in output
    assert "authorization" not in output
    assert "bearer" not in output
