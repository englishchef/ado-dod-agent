"""Tests for the DoD Key Vault JSON config contract."""

from __future__ import annotations

from backend.app.core.enterprise_config import validate_key_vault_config_contract

VALID_CONTRACT = {
    "DOD_STORAGE_BACKEND": "cosmos",
    "COSMOS_AUTH_MODE": "default_credential",
    "COSMOS_ENDPOINT": "https://example-cosmos.documents.azure.com:443/",
    "COSMOS_DATABASE": "dod-agent-dev",
    "COSMOS_CONTAINER": "dod-runs",
    "ADO_ORGANIZATION": "example-org",
    "AZURE_OPENAI_ENDPOINT": "https://example-openai.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "example-deployment",
    "LANGSMITH_PROJECT": "dod-agent-dev",
}


def test_valid_enterprise_key_vault_contract_passes() -> None:
    assert validate_key_vault_config_contract(VALID_CONTRACT) == []


def test_enterprise_contract_requires_default_credential_for_sample() -> None:
    errors = validate_key_vault_config_contract({**VALID_CONTRACT, "COSMOS_AUTH_MODE": "key"})

    assert any("COSMOS_KEY is required" in error for error in errors)


def test_contract_requires_expected_top_level_keys() -> None:
    errors = validate_key_vault_config_contract({})

    assert errors
    assert "DOD_STORAGE_BACKEND" in errors[0]


def test_contract_rejects_artifact_payload_keys() -> None:
    errors = validate_key_vault_config_contract(
        {**VALID_CONTRACT, "raw_ado_payload": {"value": "do-not-store"}}
    )

    assert any("must not store generated artifacts" in error for error in errors)


def test_agent_config_contract_rejects_actual_langgraph_api_key() -> None:
    errors = validate_key_vault_config_contract(
        {**VALID_CONTRACT, "LANGGRAPH_API_KEY": "do-not-store-here"}
    )

    assert any("must not store generated artifacts" in error for error in errors)
