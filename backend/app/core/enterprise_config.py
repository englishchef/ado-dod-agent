"""Enterprise runtime config resolution for the DoD agent."""

from __future__ import annotations

import json
import os
import warnings
from collections.abc import Callable, Mapping
from typing import Any

from backend.app.core.azure_credentials import (
    AZURE_CREDENTIAL_MODE,
    AZURE_USER_ASSIGNED_CLIENT_ID,
    get_azure_credential,
)

AGENT_CONFIG_KEY_VAULT_URL = "AGENT_CONFIG_KEY_VAULT_URL"
AGENT_CONFIG_SECRET_NAME = "AGENT_CONFIG_SECRET_NAME"

LANGGRAPH_ASSISTANT_DEFAULT = "dod"

REQUIRED_AGENT_CONFIG_KEYS = {
    "DOD_STORAGE_BACKEND",
    "COSMOS_AUTH_MODE",
    "COSMOS_ENDPOINT",
    "COSMOS_DATABASE",
    "COSMOS_CONTAINER",
    "ADO_ORGANIZATION",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_DEPLOYMENT",
    "LANGSMITH_PROJECT",
}

FORBIDDEN_AGENT_CONFIG_KEY_PATTERNS = {
    "artifact",
    "raw_ado_payload",
    "ado_payload",
    "service_now_payload",
    "servicenow_payload",
    "generated",
}
FORBIDDEN_AGENT_CONFIG_KEYS = {
    "langgraph_api_key",
    "langgraph_api_key_value",
    "langgraph_api_key_secret",
}

SUPPORTED_RUNTIME_CONFIG_KEYS = {
    "APP_ENV",
    "APP_HOST",
    "APP_PORT",
    "LOG_LEVEL",
    "AZURE_TENANT_ID",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    AZURE_CREDENTIAL_MODE,
    AZURE_USER_ASSIGNED_CLIENT_ID,
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_AUTH_MODE",
    "LLM_TEMPERATURE",
    "LLM_MAX_TOKENS",
    "LLM_TIMEOUT_SECONDS",
    "ADO_ORGANIZATION",
    "ADO_PROJECT",
    "ADO_API_VERSION",
    "ADO_AUTH_MODE",
    "DATA_DIR",
    "DOD_STORAGE_BACKEND",
    "COSMOS_AUTH_MODE",
    "COSMOS_ENDPOINT",
    "COSMOS_KEY",
    "COSMOS_DATABASE",
    "COSMOS_CONTAINER",
    "COSMOS_DISABLE_TLS_VERIFY",
    "DOD_GRAPH_NAME",
    "DOD_ASSISTANT_NAME",
    "DOD_TRACE_MODE",
    "LANGSMITH_TRACING",
    "TRACING_ENABLED",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_TLS_VERIFY",
    "LANGSMITH_CA_BUNDLE",
    "LANGGRAPH_API_URL",
    "LANGGRAPH_ASSISTANT_ID",
    "LANGGRAPH_API_KEY_HEADER",
    "LANGGRAPH_KEY_VAULT_URL",
    "LANGGRAPH_KEY_VAULT_SECRET_NAME",
    AGENT_CONFIG_KEY_VAULT_URL,
    AGENT_CONFIG_SECRET_NAME,
}


class EnterpriseConfigError(ValueError):
    """Raised when enterprise config cannot be resolved safely."""


def create_default_azure_credential(environ: Mapping[str, str] | None = None) -> Any:
    """Backward-compatible wrapper for the centralized Azure credential factory."""

    return get_azure_credential(environ)


def load_agent_config_from_key_vault(
    *,
    strict: bool = False,
    key_vault_url: str | None = None,
    secret_name: str | None = None,
    environ: Mapping[str, str] | None = None,
    credential_factory: Callable[[Mapping[str, str]], Any] | None = None,
    secret_client_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Load optional agent config JSON from Key Vault without printing values."""

    env = os.environ if environ is None else environ
    vault_url = _present_value(key_vault_url) or _present_value(
        env.get(AGENT_CONFIG_KEY_VAULT_URL)
    )
    name = _present_value(secret_name) or _present_value(env.get(AGENT_CONFIG_SECRET_NAME))
    if not vault_url and not name:
        return {}
    if not vault_url or not name:
        message = (
            "Both AGENT_CONFIG_KEY_VAULT_URL and AGENT_CONFIG_SECRET_NAME are required "
            "when either one is set."
        )
        if strict:
            raise EnterpriseConfigError(message)
        warnings.warn(message, RuntimeWarning, stacklevel=2)
        return {}

    credential = (
        credential_factory(env) if credential_factory else get_azure_credential(env)
    )
    if secret_client_factory is None:
        from azure.keyvault.secrets import SecretClient

        secret_client_factory = SecretClient

    client = secret_client_factory(vault_url=vault_url, credential=credential)
    secret = client.get_secret(name)
    return parse_agent_config_json(str(secret.value))


def parse_agent_config_json(raw_value: str) -> dict[str, Any]:
    """Parse and validate the DoD agent Key Vault JSON config contract."""

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise EnterpriseConfigError("Agent config secret must contain valid JSON.") from exc
    if not isinstance(payload, dict):
        raise EnterpriseConfigError("Agent config secret must contain a JSON object.")
    return {str(key): value for key, value in payload.items()}


def validate_key_vault_config_contract(config: Mapping[str, Any]) -> list[str]:
    """Validate key names and required enterprise config shape without values."""

    errors: list[str] = []
    missing = sorted(
        key for key in REQUIRED_AGENT_CONFIG_KEYS if not _present_value(config.get(key))
    )
    if missing:
        errors.append("Agent config secret is missing required keys: " + ", ".join(missing) + ".")

    storage_backend = str(config.get("DOD_STORAGE_BACKEND") or "").strip().lower()
    if storage_backend and storage_backend != "cosmos":
        errors.append("Enterprise agent config should set DOD_STORAGE_BACKEND=cosmos.")

    auth_mode = str(config.get("COSMOS_AUTH_MODE") or "").strip().lower()
    if auth_mode and auth_mode not in {"default_credential", "key", "emulator_key"}:
        errors.append(
            "COSMOS_AUTH_MODE must be one of: default_credential, emulator_key, key."
        )
    if auth_mode == "default_credential" and _present_value(config.get("COSMOS_KEY")):
        errors.append("COSMOS_KEY should not be set when COSMOS_AUTH_MODE=default_credential.")
    if auth_mode in {"key", "emulator_key"} and not _present_value(config.get("COSMOS_KEY")):
        errors.append(f"COSMOS_KEY is required when COSMOS_AUTH_MODE={auth_mode}.")

    forbidden = sorted(
        key
        for key in config
        if str(key).strip().lower() in FORBIDDEN_AGENT_CONFIG_KEYS
        or any(
            pattern in str(key).strip().lower()
            for pattern in FORBIDDEN_AGENT_CONFIG_KEY_PATTERNS
        )
    )
    if forbidden:
        errors.append(
            "Agent config secret must not store generated artifacts or raw payload keys: "
            + ", ".join(forbidden)
            + "."
        )
    return errors


def resolve_runtime_config(
    *,
    environ: Mapping[str, str] | None = None,
    key_vault_config: Mapping[str, Any] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Resolve enterprise runtime config with process env overriding Key Vault JSON."""

    env = os.environ if environ is None else environ
    if key_vault_config is None:
        key_vault_config = load_agent_config_from_key_vault(strict=strict, environ=env)

    resolved: dict[str, Any] = {
        str(key): value
        for key, value in key_vault_config.items()
        if str(key) in SUPPORTED_RUNTIME_CONFIG_KEYS
    }
    for key in SUPPORTED_RUNTIME_CONFIG_KEYS:
        if key in env:
            resolved[key] = env[key]
    return resolved


def validate_agent_config_pointer(
    *,
    strict: bool,
    environ: Mapping[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return safe validation errors/warnings for the optional Key Vault pointer."""

    env = os.environ if environ is None else environ
    has_url = bool(_present_value(env.get(AGENT_CONFIG_KEY_VAULT_URL)))
    has_name = bool(_present_value(env.get(AGENT_CONFIG_SECRET_NAME)))
    if has_url == has_name:
        return [], []
    message = (
        "Both AGENT_CONFIG_KEY_VAULT_URL and AGENT_CONFIG_SECRET_NAME are required "
        "when either one is set."
    )
    if strict:
        return [message], []
    return [], [message]


def _present_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
