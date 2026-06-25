"""Tests for enterprise runtime config smoke scripts."""

from __future__ import annotations

from typing import Any

from scripts import smoke_enterprise_runtime_config, smoke_keyvault_config


def test_enterprise_runtime_smoke_default_mode_does_not_call_azure(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    def fail_if_called(*_: Any, **__: Any) -> dict[str, Any]:
        raise AssertionError("Azure should not be called in offline smoke mode.")

    monkeypatch.setattr(
        smoke_enterprise_runtime_config,
        "load_agent_config_from_key_vault",
        fail_if_called,
    )

    assert smoke_enterprise_runtime_config.main([]) == 0
    output = capsys.readouterr().out
    assert "status: ok" in output
    assert "Secret values are intentionally not printed." in output


def test_keyvault_config_smoke_imports_without_calling_azure(monkeypatch: Any) -> None:
    calls: list[str] = []

    def fake_loader(*_: Any, **__: Any) -> dict[str, Any]:
        calls.append("called")
        return {"DOD_STORAGE_BACKEND": "cosmos"}

    monkeypatch.setattr(smoke_keyvault_config, "load_agent_config_from_key_vault", fake_loader)

    assert calls == []
