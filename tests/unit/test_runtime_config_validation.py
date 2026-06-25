"""Tests for runtime configuration validation smoke helpers."""

from __future__ import annotations

from backend.app.utils.config import Settings
from scripts.smoke_runtime_config import validate_runtime_config


def test_runtime_config_local_json_does_not_require_cosmos_config() -> None:
    result = validate_runtime_config(
        Settings(
            APP_ENV="local",
            DOD_STORAGE_BACKEND="local_json",
            COSMOS_ENDPOINT=None,
            COSMOS_DATABASE=None,
            COSMOS_CONTAINER=None,
            COSMOS_KEY=None,
        ),
        mode="local",
    )

    assert result.ok
    assert not any("COSMOS" in item for item in result.errors)


def test_runtime_config_cosmos_requires_endpoint_database_and_container() -> None:
    result = validate_runtime_config(
        Settings(
            DOD_STORAGE_BACKEND="cosmos",
            COSMOS_AUTH_MODE="default_credential",
            COSMOS_ENDPOINT=None,
            COSMOS_DATABASE=None,
            COSMOS_CONTAINER=None,
            COSMOS_KEY=None,
        ),
        mode="container",
    )

    assert not result.ok
    assert "COSMOS_ENDPOINT is required." in result.errors
    assert "COSMOS_DATABASE is required." in result.errors
    assert "COSMOS_CONTAINER is required." in result.errors


def test_runtime_config_emulator_key_requires_cosmos_key() -> None:
    result = validate_runtime_config(
        Settings(
            DOD_STORAGE_BACKEND="cosmos",
            COSMOS_AUTH_MODE="emulator_key",
            COSMOS_ENDPOINT="https://localhost:8081",
            COSMOS_DATABASE="dod_agent_local",
            COSMOS_CONTAINER="dod_runs",
            COSMOS_KEY=None,
        ),
        mode="local",
    )

    assert not result.ok
    assert "COSMOS_KEY is required." in result.errors


def test_runtime_config_key_requires_cosmos_key() -> None:
    result = validate_runtime_config(
        Settings(
            DOD_STORAGE_BACKEND="cosmos",
            COSMOS_AUTH_MODE="key",
            COSMOS_ENDPOINT="https://example.documents.azure.com:443/",
            COSMOS_DATABASE="dod_agent",
            COSMOS_CONTAINER="dod_runs",
            COSMOS_KEY=None,
        ),
        mode="container",
    )

    assert not result.ok
    assert "COSMOS_KEY is required." in result.errors


def test_runtime_config_default_credential_does_not_require_cosmos_key() -> None:
    result = validate_runtime_config(
        Settings(
            DOD_STORAGE_BACKEND="cosmos",
            COSMOS_AUTH_MODE="default_credential",
            COSMOS_ENDPOINT="https://example.documents.azure.com:443/",
            COSMOS_DATABASE="dod_agent",
            COSMOS_CONTAINER="dod_runs",
            COSMOS_KEY=None,
        ),
        mode="container",
    )

    assert result.ok
    assert not any(item == "COSMOS_KEY is required." for item in result.errors)


def test_runtime_config_production_like_strict_rejects_local_json() -> None:
    result = validate_runtime_config(
        Settings(APP_ENV="production", DOD_STORAGE_BACKEND="local_json"),
        mode="container",
        strict=True,
    )

    assert not result.ok
    assert (
        "Production-like/container runtime should use DOD_STORAGE_BACKEND=cosmos."
        in result.errors
    )


def test_runtime_config_langsmith_disabled_does_not_require_langsmith_config() -> None:
    result = validate_runtime_config(
        Settings(LANGSMITH_TRACING=False, LANGSMITH_PROJECT=""),
        mode="local",
        check_langsmith=False,
    )

    assert result.ok
    assert not any("LANGSMITH" in item for item in result.errors)


def test_runtime_config_client_secret_mode_requires_secret_fields() -> None:
    result = validate_runtime_config(
        Settings(_env_file=None, AZURE_CREDENTIAL_MODE="client_secret"),
        mode="local",
    )

    assert not result.ok
    assert any("AZURE_CLIENT_ID is required" in item for item in result.errors)
    assert any("AZURE_TENANT_ID is required" in item for item in result.errors)
    assert any("AZURE_CLIENT_SECRET is required" in item for item in result.errors)


def test_runtime_config_invalid_azure_credential_mode_fails_clearly() -> None:
    result = validate_runtime_config(
        Settings(_env_file=None, AZURE_CREDENTIAL_MODE="invalid"),
        mode="local",
    )

    assert not result.ok
    assert any("AZURE_CREDENTIAL_MODE" in item for item in result.errors)
