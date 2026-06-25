"""Tests for LangSmith tracing config aliases."""

from __future__ import annotations

from typing import Any

from backend.app.services.observability import langsmith_tracing
from backend.app.utils.config import Settings


def test_langsmith_tracing_wins_over_tracing_enabled(monkeypatch: Any) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("TRACING_ENABLED", "true")

    assert langsmith_tracing.is_tracing_enabled() is False


def test_tracing_enabled_alias_works_when_langsmith_tracing_absent(monkeypatch: Any) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.setenv("TRACING_ENABLED", "true")

    assert langsmith_tracing.is_tracing_enabled() is True


def test_settings_applies_tracing_enabled_alias_when_canonical_absent() -> None:
    settings = Settings(_env_file=None, LANGSMITH_TRACING=None, TRACING_ENABLED=True)

    assert settings.LANGSMITH_TRACING is True
