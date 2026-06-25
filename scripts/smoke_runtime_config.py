"""Validate DoD runtime configuration without external service calls."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from backend.app.core.azure_credentials import (
        get_redacted_credential_summary,
        validate_azure_credential_config,
    )
    from backend.app.core.enterprise_config import (
        AGENT_CONFIG_KEY_VAULT_URL,
        AGENT_CONFIG_SECRET_NAME,
        validate_agent_config_pointer,
    )
    from backend.app.core.langgraph_api_key import (
        get_redacted_langgraph_api_key_summary,
        validate_langgraph_api_key_config,
    )
    from backend.app.utils.config import Settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.core.azure_credentials import (
        get_redacted_credential_summary,
        validate_azure_credential_config,
    )
    from backend.app.core.enterprise_config import (
        AGENT_CONFIG_KEY_VAULT_URL,
        AGENT_CONFIG_SECRET_NAME,
        validate_agent_config_pointer,
    )
    from backend.app.core.langgraph_api_key import (
        get_redacted_langgraph_api_key_summary,
        validate_langgraph_api_key_config,
    )
    from backend.app.utils.config import Settings

VALID_STORAGE_BACKENDS = {"local_json", "cosmos"}
VALID_COSMOS_AUTH_MODES = {"emulator_key", "key", "default_credential"}
PRODUCTION_LIKE_ENVS = {"prod", "production", "enterprise", "dev", "container"}


@dataclass
class RuntimeConfigValidation:
    """Safe validation result for runtime configuration."""

    mode: str
    storage_backend: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    configured: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_runtime_config(
    settings: Settings,
    *,
    mode: str,
    strict: bool = False,
    check_langsmith: bool = False,
    check_cosmos_config_only: bool = False,
) -> RuntimeConfigValidation:
    """Validate config presence without calling remote services."""

    storage_backend = str(settings.DOD_STORAGE_BACKEND or "local_json").strip().lower()
    result = RuntimeConfigValidation(mode=mode, storage_backend=storage_backend)
    _require_present(result, "APP_ENV", settings.APP_ENV)
    _require_present(result, "APP_HOST", settings.APP_HOST)
    _require_present(result, "APP_PORT", settings.APP_PORT)
    _require_present(result, "DOD_GRAPH_NAME", settings.DOD_GRAPH_NAME)
    _require_present(result, "DOD_ASSISTANT_NAME", settings.DOD_ASSISTANT_NAME)
    _validate_azure_credentials(settings, result)
    _validate_agent_config_pointer(result, mode=mode, strict=strict)
    _validate_langgraph_platform_config(settings, result, strict)

    if storage_backend not in VALID_STORAGE_BACKENDS:
        result.errors.append("DOD_STORAGE_BACKEND must be one of: cosmos, local_json.")
    elif storage_backend == "cosmos" or check_cosmos_config_only:
        _validate_cosmos_config(settings, result)
    else:
        _configured(result, "DOD_STORAGE_BACKEND")

    production_like = mode == "container" or _is_production_like(settings.APP_ENV)
    if production_like and storage_backend == "local_json":
        message = "Production-like/container runtime should use DOD_STORAGE_BACKEND=cosmos."
        if strict:
            result.errors.append(message)
        else:
            result.warnings.append(message)

    if _langsmith_tracing_enabled(settings) or check_langsmith:
        _validate_langsmith_config(settings, result, strict)
    else:
        _configured(result, "LANGSMITH_TRACING=false")

    return result


def build_settings(storage_backend: str | None = None) -> Settings:
    """Build settings with an optional storage backend CLI override."""

    overrides: dict[str, Any] = {}
    if storage_backend:
        overrides["DOD_STORAGE_BACKEND"] = storage_backend
    return Settings(**overrides)


def render_validation_summary(result: RuntimeConfigValidation) -> str:
    """Render a safe validation summary without secret values."""

    lines = [
        "Runtime config validation",
        f"- mode: {result.mode}",
        f"- storage_backend: {result.storage_backend}",
        f"- status: {'ok' if result.ok else 'invalid'}",
    ]
    if result.configured:
        lines.append("- configured: " + ", ".join(sorted(set(result.configured))))
    if result.warnings:
        lines.append("- warnings:")
        lines.extend(f"  - {item}" for item in result.warnings)
    if result.errors:
        lines.append("- errors:")
        lines.extend(f"  - {item}" for item in result.errors)
    lines.append("Secret values are intentionally not printed.")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate DoD runtime configuration.")
    parser.add_argument("--mode", choices=("local", "container"), default="local")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--storage-backend", choices=tuple(sorted(VALID_STORAGE_BACKENDS)))
    parser.add_argument("--check-langsmith", action="store_true")
    parser.add_argument("--check-cosmos-config-only", action="store_true")
    return parser


def _validate_cosmos_config(settings: Settings, result: RuntimeConfigValidation) -> None:
    auth_mode = settings.resolved_cosmos_auth_mode
    if auth_mode not in VALID_COSMOS_AUTH_MODES:
        result.errors.append(
            "COSMOS_AUTH_MODE must be one of: default_credential, emulator_key, key."
        )
    else:
        _configured(result, "COSMOS_AUTH_MODE")
    _require_present(result, "COSMOS_ENDPOINT", settings.resolved_cosmos_endpoint)
    _require_present(result, "COSMOS_DATABASE", settings.resolved_cosmos_database)
    _require_present(result, "COSMOS_CONTAINER", settings.resolved_cosmos_container)
    if auth_mode in {"emulator_key", "key"}:
        _require_present(result, "COSMOS_KEY", settings.resolved_cosmos_key)
    elif auth_mode == "default_credential":
        _configured(result, "COSMOS_KEY not required for default_credential")


def _validate_langsmith_config(
    settings: Settings,
    result: RuntimeConfigValidation,
    strict: bool,
) -> None:
    _configured(result, "LANGSMITH_TRACING")
    _require_present(result, "LANGSMITH_PROJECT", settings.LANGSMITH_PROJECT)
    if settings.TRACING_ENABLED is not None:
        _configured(result, "TRACING_ENABLED alias")
    if settings.LANGSMITH_ENDPOINT:
        _configured(result, "LANGSMITH_ENDPOINT")
    if settings.LANGSMITH_TLS_VERIFY is not None:
        _configured(result, "LANGSMITH_TLS_VERIFY")
    if settings.LANGSMITH_CA_BUNDLE:
        _configured(result, "LANGSMITH_CA_BUNDLE")
    if not _is_present(os.environ.get("LANGSMITH_API_KEY")):
        message = "LANGSMITH_API_KEY is not set; hosted LangSmith traces may not be submitted."
        if strict and _langsmith_tracing_enabled(settings):
            result.errors.append(message)
        else:
            result.warnings.append(message)


def _validate_azure_credentials(settings: Settings, result: RuntimeConfigValidation) -> None:
    environ = {
        "AZURE_CREDENTIAL_MODE": settings.AZURE_CREDENTIAL_MODE,
        "AZURE_CLIENT_ID": settings.AZURE_CLIENT_ID or "",
        "AZURE_USER_ASSIGNED_CLIENT_ID": settings.AZURE_USER_ASSIGNED_CLIENT_ID or "",
        "AZURE_TENANT_ID": settings.AZURE_TENANT_ID or "",
        "AZURE_CLIENT_SECRET": settings.AZURE_CLIENT_SECRET or "",
    }
    errors = validate_azure_credential_config(environ)
    result.errors.extend(errors)
    if not errors:
        summary = get_redacted_credential_summary(environ)
        _configured(result, f"AZURE_CREDENTIAL_MODE={summary.mode}")
        _configured(
            result,
            "AZURE_CLIENT_ID configured="
            + ("yes" if summary.client_id_configured else "no"),
        )
        _configured(
            result,
            "AZURE_TENANT_ID configured="
            + ("yes" if summary.tenant_id_configured else "no"),
        )
        _configured(
            result,
            "AZURE_CLIENT_SECRET configured="
            + ("yes" if summary.client_secret_configured else "no"),
        )


def _validate_agent_config_pointer(
    result: RuntimeConfigValidation,
    *,
    mode: str,
    strict: bool,
) -> None:
    pointer_errors, pointer_warnings = validate_agent_config_pointer(
        strict=strict or mode == "container"
    )
    result.errors.extend(pointer_errors)
    result.warnings.extend(pointer_warnings)
    if os.environ.get(AGENT_CONFIG_KEY_VAULT_URL):
        _configured(result, AGENT_CONFIG_KEY_VAULT_URL)
    if os.environ.get(AGENT_CONFIG_SECRET_NAME):
        _configured(result, AGENT_CONFIG_SECRET_NAME)


def _validate_langgraph_platform_config(
    settings: Settings,
    result: RuntimeConfigValidation,
    strict: bool,
) -> None:
    assistant_id = settings.resolved_langgraph_assistant_id
    if assistant_id != "dod":
        message = "LANGGRAPH_ASSISTANT_ID should resolve to dod for the DoD graph."
        if strict:
            result.errors.append(message)
        else:
            result.warnings.append(message)
    else:
        _configured(result, "LANGGRAPH_ASSISTANT_ID=dod")
    for name in (
        "LANGGRAPH_API_URL",
        "LANGGRAPH_API_KEY_HEADER",
        "LANGGRAPH_KEY_VAULT_URL",
        "LANGGRAPH_KEY_VAULT_SECRET_NAME",
    ):
        if _is_present(getattr(settings, name)):
            _configured(result, name)
    environ = {
        "LANGGRAPH_API_URL": settings.LANGGRAPH_API_URL or "",
        "LANGGRAPH_ASSISTANT_ID": settings.resolved_langgraph_assistant_id,
        "LANGGRAPH_API_KEY_HEADER": settings.LANGGRAPH_API_KEY_HEADER or "",
        "LANGGRAPH_KEY_VAULT_URL": settings.LANGGRAPH_KEY_VAULT_URL or "",
        "LANGGRAPH_KEY_VAULT_SECRET_NAME": settings.LANGGRAPH_KEY_VAULT_SECRET_NAME or "",
    }
    for item in validate_langgraph_api_key_config(strict=False, environ=environ):
        result.warnings.append(item)
    summary = get_redacted_langgraph_api_key_summary(environ)
    _configured(
        result,
        "LANGGRAPH_KEY_VAULT_URL configured="
        + ("yes" if summary["key_vault_url_configured"] else "no"),
    )
    _configured(
        result,
        "LANGGRAPH_KEY_VAULT_SECRET_NAME configured="
        + ("yes" if summary["key_vault_secret_name_configured"] else "no"),
    )


def _require_present(result: RuntimeConfigValidation, name: str, value: Any) -> None:
    if _is_present(value):
        _configured(result, name)
    else:
        result.errors.append(f"{name} is required.")


def _configured(result: RuntimeConfigValidation, name: str) -> None:
    result.configured.append(name)


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _is_production_like(app_env: str | None) -> bool:
    return str(app_env or "").strip().lower() in PRODUCTION_LIKE_ENVS


def _langsmith_tracing_enabled(settings: Settings) -> bool:
    if settings.LANGSMITH_TRACING is not None:
        return bool(settings.LANGSMITH_TRACING)
    return bool(settings.TRACING_ENABLED)


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = build_settings(args.storage_backend)
    result = validate_runtime_config(
        settings,
        mode=args.mode,
        strict=args.strict,
        check_langsmith=args.check_langsmith,
        check_cosmos_config_only=args.check_cosmos_config_only,
    )
    print(render_validation_summary(result))
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
