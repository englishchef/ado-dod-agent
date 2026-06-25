"""Tests for enterprise runtime config merge precedence."""

from __future__ import annotations

from backend.app.core.enterprise_config import resolve_runtime_config
from backend.app.utils.config import Settings


def test_env_vars_override_key_vault_json_values() -> None:
    resolved = resolve_runtime_config(
        environ={"COSMOS_DATABASE": "env-db"},
        key_vault_config={"COSMOS_DATABASE": "kv-db", "COSMOS_CONTAINER": "kv-container"},
    )

    assert resolved["COSMOS_DATABASE"] == "env-db"
    assert resolved["COSMOS_CONTAINER"] == "kv-container"


def test_key_vault_json_fills_missing_env_values() -> None:
    resolved = resolve_runtime_config(
        environ={},
        key_vault_config={"DOD_STORAGE_BACKEND": "cosmos"},
    )

    assert resolved["DOD_STORAGE_BACKEND"] == "cosmos"


def test_langgraph_assistant_id_defaults_to_dod() -> None:
    assert Settings(_env_file=None).resolved_langgraph_assistant_id == "dod"
