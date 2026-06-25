"""Smoke-check enterprise runtime config resolution without Azure by default."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from backend.app.core.azure_credentials import (
        get_redacted_credential_summary,
        validate_azure_credential_config,
    )
    from backend.app.core.enterprise_config import (
        AGENT_CONFIG_KEY_VAULT_URL,
        AGENT_CONFIG_SECRET_NAME,
        EnterpriseConfigError,
        load_agent_config_from_key_vault,
        parse_agent_config_json,
        resolve_runtime_config,
        validate_agent_config_pointer,
        validate_key_vault_config_contract,
    )
    from backend.app.core.langgraph_api_key import validate_langgraph_api_key_config
    from backend.app.utils.config import Settings

    from scripts.smoke_runtime_config import validate_runtime_config
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise

    from backend.app.core.azure_credentials import (
        get_redacted_credential_summary,
        validate_azure_credential_config,
    )
    from backend.app.core.enterprise_config import (
        AGENT_CONFIG_KEY_VAULT_URL,
        AGENT_CONFIG_SECRET_NAME,
        EnterpriseConfigError,
        load_agent_config_from_key_vault,
        parse_agent_config_json,
        resolve_runtime_config,
        validate_agent_config_pointer,
        validate_key_vault_config_contract,
    )
    from backend.app.core.langgraph_api_key import validate_langgraph_api_key_config
    from backend.app.utils.config import Settings

    from scripts.smoke_runtime_config import validate_runtime_config


PLACEHOLDER_KEY_VAULT_CONFIG: dict[str, Any] = {
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

CONFIRMED_ENTERPRISE_ENV_KEYS = {
    AGENT_CONFIG_KEY_VAULT_URL,
    AGENT_CONFIG_SECRET_NAME,
    "LANGSMITH_TRACING",
    "AZURE_CREDENTIAL_MODE",
    "TRACING_ENABLED",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_TLS_VERIFY",
    "LANGSMITH_CA_BUNDLE",
    "LANGGRAPH_API_URL",
    "LANGGRAPH_ASSISTANT_ID",
    "LANGGRAPH_API_KEY_HEADER",
    "LANGGRAPH_KEY_VAULT_URL",
    "LANGGRAPH_KEY_VAULT_SECRET_NAME",
}


def load_mock_key_vault_config(path: Path | None) -> dict[str, Any]:
    """Load a local placeholder JSON object for offline Key Vault simulation."""

    if path is None:
        return dict(PLACEHOLDER_KEY_VAULT_CONFIG)
    return parse_agent_config_json(path.read_text(encoding="utf-8"))


def build_settings_from_sources(
    *,
    environ: Mapping[str, str],
    key_vault_config: Mapping[str, Any],
    strict: bool,
) -> Settings:
    """Build Settings from deterministic enterprise precedence inputs."""

    resolved = resolve_runtime_config(
        environ=environ,
        key_vault_config=key_vault_config,
        strict=strict,
    )
    return Settings(_env_file=None, **resolved)


def run_offline_checks(args: argparse.Namespace) -> tuple[list[str], list[str], list[str]]:
    """Run config checks that must not call Azure, Cosmos, ADO, LLM, or LangSmith."""

    errors: list[str] = []
    warnings: list[str] = []
    resolved_keys: list[str] = []
    key_vault_config = load_mock_key_vault_config(args.mock_keyvault_json)
    errors.extend(validate_key_vault_config_contract(key_vault_config))

    pointer_errors, pointer_warnings = validate_agent_config_pointer(
        strict=args.strict,
        environ={
            AGENT_CONFIG_KEY_VAULT_URL: args.key_vault_url or "",
            AGENT_CONFIG_SECRET_NAME: args.config_secret_name or "",
        },
    )
    errors.extend(pointer_errors)
    warnings.extend(pointer_warnings)

    direct_env = {
        "DOD_STORAGE_BACKEND": "cosmos",
        "AZURE_CREDENTIAL_MODE": "managed_identity",
        "COSMOS_AUTH_MODE": "default_credential",
        "COSMOS_ENDPOINT": "https://direct-cosmos.documents.azure.com:443/",
        "COSMOS_DATABASE": "direct-db",
        "COSMOS_CONTAINER": "direct-runs",
        "LANGSMITH_TRACING": "false",
        "TRACING_ENABLED": "true",
        "LANGSMITH_ENDPOINT": "https://api.smith.langchain.com",
        "LANGSMITH_TLS_VERIFY": "true",
        "LANGSMITH_CA_BUNDLE": "",
        "LANGGRAPH_API_URL": "https://langgraph.example",
        "LANGGRAPH_ASSISTANT_ID": "dod",
        "LANGGRAPH_API_KEY_HEADER": "x-api-key",
        "LANGGRAPH_KEY_VAULT_URL": "https://vault.example/",
        "LANGGRAPH_KEY_VAULT_SECRET_NAME": "langgraph-api-key",
        AGENT_CONFIG_KEY_VAULT_URL: "https://agent-config.example/",
        AGENT_CONFIG_SECRET_NAME: "dod-agent-config",
    }
    direct_resolved = resolve_runtime_config(
        environ=direct_env,
        key_vault_config={},
        strict=args.strict,
    )
    missing_confirmed = sorted(CONFIRMED_ENTERPRISE_ENV_KEYS - direct_resolved.keys())
    if missing_confirmed:
        errors.append(
            "Enterprise runtime config did not recognize expected keys: "
            + ", ".join(missing_confirmed)
            + "."
        )
    errors.extend(validate_azure_credential_config(direct_env))
    errors.extend(validate_langgraph_api_key_config(strict=False, environ=direct_env))
    direct_settings = build_settings_from_sources(
        environ=direct_env,
        key_vault_config={},
        strict=args.strict,
    )
    direct_result = validate_runtime_config(
        direct_settings,
        mode="container" if args.strict else "local",
        strict=args.strict,
        check_cosmos_config_only=args.check_cosmos_default_credential,
    )
    errors.extend(direct_result.errors)
    warnings.extend(direct_result.warnings)

    precedence_env = {
        "COSMOS_DATABASE": "env-wins",
        "LANGSMITH_TRACING": "false",
        "TRACING_ENABLED": "true",
        "LANGGRAPH_ASSISTANT_ID": "dod",
    }
    merged = resolve_runtime_config(
        environ=precedence_env,
        key_vault_config=key_vault_config,
        strict=args.strict,
    )
    if merged.get("COSMOS_DATABASE") != "env-wins":
        errors.append("Environment variables did not override Key Vault JSON config.")
    if merged.get("COSMOS_CONTAINER") != key_vault_config.get("COSMOS_CONTAINER"):
        errors.append("Key Vault JSON config did not fill missing environment values.")
    resolved_keys = sorted(merged.keys())
    merged_settings = Settings(_env_file=None, **merged)
    merged_result = validate_runtime_config(
        merged_settings,
        mode="container" if args.strict else "local",
        strict=args.strict,
        check_langsmith=True,
        check_cosmos_config_only=True,
    )
    errors.extend(merged_result.errors)
    warnings.extend(merged_result.warnings)
    if merged_settings.resolved_langgraph_assistant_id != "dod":
        errors.append("LANGGRAPH_ASSISTANT_ID did not resolve to dod.")
    if merged_settings.LANGSMITH_TRACING is not False:
        errors.append("LANGSMITH_TRACING did not take precedence over TRACING_ENABLED.")

    alias_settings = Settings(_env_file=None, TRACING_ENABLED=True, LANGSMITH_TRACING=None)
    if alias_settings.LANGSMITH_TRACING is not True:
        errors.append("TRACING_ENABLED alias was not honored when LANGSMITH_TRACING was absent.")

    credential_summary = get_redacted_credential_summary(direct_env)
    resolved_keys.extend(
        [
            f"AZURE_CREDENTIAL_MODE={credential_summary.mode}",
            "AZURE_CLIENT_ID configured="
            + ("yes" if credential_summary.client_id_configured else "no"),
            "AZURE_TENANT_ID configured="
            + ("yes" if credential_summary.tenant_id_configured else "no"),
            "AZURE_CLIENT_SECRET configured="
            + ("yes" if credential_summary.client_secret_configured else "no"),
        ]
    )
    return errors, warnings, sorted(set(resolved_keys))


def run_live_key_vault_check(args: argparse.Namespace) -> tuple[list[str], list[str], list[str]]:
    """Fetch live Key Vault JSON only when explicitly requested."""

    environ = dict(os.environ)
    if args.key_vault_url:
        environ[AGENT_CONFIG_KEY_VAULT_URL] = args.key_vault_url
    if args.config_secret_name:
        environ[AGENT_CONFIG_SECRET_NAME] = args.config_secret_name
    config = load_agent_config_from_key_vault(strict=True, environ=environ)
    errors = validate_key_vault_config_contract(config)
    settings = build_settings_from_sources(
        environ=environ,
        key_vault_config=config,
        strict=args.strict,
    )
    result = validate_runtime_config(settings, mode="container", strict=args.strict)
    errors.extend(result.errors)
    return errors, result.warnings, sorted(config.keys())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate enterprise DoD runtime config resolution safely."
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mock-keyvault-json", type=Path, default=None)
    parser.add_argument("--live-keyvault", action="store_true")
    parser.add_argument("--config-secret-name", default=None)
    parser.add_argument("--key-vault-url", default=None)
    parser.add_argument("--check-cosmos-default-credential", action="store_true")
    parser.add_argument("--print-resolved-keys", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.live_keyvault:
            errors, warnings, resolved_keys = run_live_key_vault_check(args)
        else:
            errors, warnings, resolved_keys = run_offline_checks(args)
    except (EnterpriseConfigError, OSError, ValueError, ModuleNotFoundError) as exc:
        print(f"Error: enterprise runtime config smoke failed: {type(exc).__name__}: {exc}")
        return 2

    print("Enterprise runtime config smoke")
    print(f"- mode: {'live-keyvault' if args.live_keyvault else 'offline'}")
    print(f"- status: {'ok' if not errors else 'invalid'}")
    if args.print_resolved_keys:
        print("- resolved_keys: " + ", ".join(resolved_keys))
    if warnings:
        print("- warnings:")
        for item in warnings:
            print(f"  - {item}")
    if errors:
        print("- errors:")
        for item in errors:
            print(f"  - {item}")
    print("Secret values are intentionally not printed.")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
