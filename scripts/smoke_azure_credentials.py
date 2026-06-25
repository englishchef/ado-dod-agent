"""Validate Azure credential configuration without live Azure calls by default."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.azure_credentials import (  # noqa: E402
    AzureCredentialConfigError,
    get_azure_credential,
    get_redacted_credential_summary,
    validate_azure_credential_config,
)
from backend.app.core.enterprise_config import (  # noqa: E402
    load_agent_config_from_key_vault,
    parse_agent_config_json,
)

COSMOS_SCOPE = "https://cosmos.azure.com/.default"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Azure credential configuration.")
    parser.add_argument("--live-keyvault", action="store_true")
    parser.add_argument("--live-cosmos-token", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    errors = validate_azure_credential_config()
    summary = get_redacted_credential_summary()

    print("Azure credential smoke")
    for line in summary.lines():
        print(f"- {line}")

    credential = None
    if not errors:
        try:
            credential = get_azure_credential()
            print(f"- credential_type: {type(credential).__name__}")
        except (AzureCredentialConfigError, ModuleNotFoundError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")

    if args.live_keyvault and not errors:
        try:
            config = load_agent_config_from_key_vault(strict=True)
            parse_agent_config_json("{}")
            print(f"- live_keyvault_secret_keys: {len(config)}")
        except Exception as exc:
            errors.append(f"Live Key Vault check failed: {type(exc).__name__}: {exc}")

    if args.live_cosmos_token and not errors:
        try:
            if credential is None:
                credential = get_azure_credential()
            token = credential.get_token(COSMOS_SCOPE)
            if not getattr(token, "token", None):
                errors.append("Live Cosmos token check did not return a token.")
            else:
                print("- live_cosmos_token_acquired: true")
        except Exception as exc:
            errors.append(f"Live Cosmos token check failed: {type(exc).__name__}: {exc}")

    if errors:
        print("- status: invalid")
        print("- errors:")
        for item in errors:
            print(f"  - {item}")
    else:
        print("- status: ok")
    print("Credential values and secrets are intentionally not printed.")
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
