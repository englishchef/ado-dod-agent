"""Tests for confirmed enterprise deployment configuration clarifications."""

from __future__ import annotations

from backend.app.utils.config import Settings
from scripts.smoke_runtime_config import validate_runtime_config


def test_langgraph_assistant_id_dod_is_accepted() -> None:
    result = validate_runtime_config(
        Settings(_env_file=None, LANGGRAPH_ASSISTANT_ID="dod"),
        mode="local",
    )

    assert result.ok
    assert "LANGGRAPH_ASSISTANT_ID=dod" in result.configured


def test_non_dod_assistant_id_warns_or_fails_by_strict_mode() -> None:
    warning_result = validate_runtime_config(
        Settings(_env_file=None, LANGGRAPH_ASSISTANT_ID="other"),
        mode="local",
    )
    strict_result = validate_runtime_config(
        Settings(_env_file=None, LANGGRAPH_ASSISTANT_ID="other"),
        mode="local",
        strict=True,
    )

    assert any("LANGGRAPH_ASSISTANT_ID" in warning for warning in warning_result.warnings)
    assert any("LANGGRAPH_ASSISTANT_ID" in error for error in strict_result.errors)
