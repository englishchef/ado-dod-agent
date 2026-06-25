"""LangGraph API key retrieval for external invocation helpers."""

from __future__ import annotations

import os
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from backend.app.core.azure_credentials import get_azure_credential

LANGGRAPH_API_URL = "LANGGRAPH_API_URL"
LANGGRAPH_ASSISTANT_ID = "LANGGRAPH_ASSISTANT_ID"
LANGGRAPH_API_KEY_HEADER = "LANGGRAPH_API_KEY_HEADER"
LANGGRAPH_KEY_VAULT_URL = "LANGGRAPH_KEY_VAULT_URL"
LANGGRAPH_KEY_VAULT_SECRET_NAME = "LANGGRAPH_KEY_VAULT_SECRET_NAME"

DEFAULT_LANGGRAPH_ASSISTANT_ID = "dod"
DEFAULT_LANGGRAPH_API_KEY_HEADER = "x-api-key"


class LangGraphApiKeyConfigError(ValueError):
    """Raised when LangGraph API key retrieval config is invalid."""


@dataclass(frozen=True)
class LangGraphApiKeyConfig:
    """LangGraph API invocation config that is safe to summarize."""

    api_url: str | None
    assistant_id: str
    api_key_header: str
    key_vault_url: str | None
    key_vault_secret_name: str | None


def get_langgraph_api_key_config(
    environ: Mapping[str, str] | None = None,
) -> LangGraphApiKeyConfig:
    """Return LangGraph API-key config from environment with safe defaults."""

    env = os.environ if environ is None else environ
    return LangGraphApiKeyConfig(
        api_url=_present_value(env.get(LANGGRAPH_API_URL)),
        assistant_id=_present_value(env.get(LANGGRAPH_ASSISTANT_ID))
        or DEFAULT_LANGGRAPH_ASSISTANT_ID,
        api_key_header=_present_value(env.get(LANGGRAPH_API_KEY_HEADER))
        or DEFAULT_LANGGRAPH_API_KEY_HEADER,
        key_vault_url=_present_value(env.get(LANGGRAPH_KEY_VAULT_URL)),
        key_vault_secret_name=_present_value(env.get(LANGGRAPH_KEY_VAULT_SECRET_NAME)),
    )


def validate_langgraph_api_key_config(
    *,
    strict: bool = False,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """Validate LangGraph API-key Key Vault pointer without fetching the secret."""

    config = get_langgraph_api_key_config(environ)
    errors: list[str] = []
    if config.assistant_id != DEFAULT_LANGGRAPH_ASSISTANT_ID:
        errors.append("LANGGRAPH_ASSISTANT_ID should resolve to dod for the DoD graph.")
    has_vault = bool(config.key_vault_url)
    has_secret = bool(config.key_vault_secret_name)
    if has_vault != has_secret:
        errors.append(
            "Both LANGGRAPH_KEY_VAULT_URL and LANGGRAPH_KEY_VAULT_SECRET_NAME are "
            "required when either one is set."
        )
    if strict and not has_vault and not has_secret:
        errors.append(
            "LANGGRAPH_KEY_VAULT_URL and LANGGRAPH_KEY_VAULT_SECRET_NAME are required "
            "for live LangGraph API-key retrieval."
        )
    return errors


def get_redacted_langgraph_api_key_summary(
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a safe summary that never includes the API key value."""

    config = get_langgraph_api_key_config(environ)
    return {
        "api_url_configured": bool(config.api_url),
        "assistant_id": config.assistant_id,
        "api_key_header": config.api_key_header,
        "key_vault_url_configured": bool(config.key_vault_url),
        "key_vault_secret_name_configured": bool(config.key_vault_secret_name),
        "api_key_value_printed": False,
    }


def get_langgraph_api_key(
    *,
    strict: bool = False,
    environ: Mapping[str, str] | None = None,
    credential_factory: Callable[[Mapping[str, str]], Any] | None = None,
    secret_client_factory: Callable[..., Any] | None = None,
) -> str | None:
    """Fetch the LangGraph API key string from Key Vault for external callers."""

    env = os.environ if environ is None else environ
    config = get_langgraph_api_key_config(env)
    errors = validate_langgraph_api_key_config(strict=strict, environ=env)
    missing_pointer_only = (
        not strict
        and not config.key_vault_url
        and not config.key_vault_secret_name
        and errors == []
    )
    if missing_pointer_only:
        return None
    if errors:
        message = "; ".join(errors)
        if strict:
            raise LangGraphApiKeyConfigError(message)
        warnings.warn(message, RuntimeWarning, stacklevel=2)
        return None

    credential = credential_factory(env) if credential_factory else get_azure_credential(env)
    if secret_client_factory is None:
        from azure.keyvault.secrets import SecretClient

        secret_client_factory = SecretClient

    client = secret_client_factory(vault_url=config.key_vault_url, credential=credential)
    secret = client.get_secret(config.key_vault_secret_name)
    value = str(secret.value or "")
    if not value.strip():
        raise LangGraphApiKeyConfigError("LangGraph API key secret value is empty.")
    return value


def _present_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
