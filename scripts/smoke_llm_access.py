"""Smoke test Azure OpenAI-compatible Foundry model access using Entra ID."""

from __future__ import annotations

import json
from urllib.parse import urlparse

try:
    from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
    from backend.app.utils.config import get_settings


def endpoint_host(endpoint: str | None) -> str:
    """Return only the host portion of the configured endpoint."""

    if not endpoint:
        return "<missing>"
    parsed = urlparse(endpoint)
    return parsed.netloc or endpoint.split("/", maxsplit=1)[0]


def format_success_summary(
    *,
    endpoint: str | None,
    deployment: str | None,
    api_version: str | None,
    auth_mode: str,
    response: dict[str, object],
) -> str:
    """Render a non-sensitive success summary."""

    return "\n".join(
        [
            "LLM smoke test succeeded",
            f"Endpoint host: {endpoint_host(endpoint)}",
            f"Auth mode: {auth_mode}",
            f"Deployment: {deployment}",
            f"API version: {api_version}",
            f"Response: {json.dumps(response, sort_keys=True)}",
        ]
    )


def troubleshooting_guidance() -> str:
    """Return safe troubleshooting guidance without exposing credentials."""

    return "\n".join(
        [
            "Troubleshooting:",
            "- Confirm PIM role is activated.",
            "- Confirm Azure CLI login is active in the current shell/dev container.",
            "- Confirm the correct subscription and tenant are selected.",
            "- Confirm Cognitive Services OpenAI User or equivalent Foundry role is assigned "
            "at the correct scope.",
            "- Confirm endpoint, deployment, and API version are correct.",
        ]
    )


def run_smoke() -> dict[str, object]:
    """Execute the local LLM access smoke test."""

    return AzureFoundryChatClient().invoke_json_smoke()


def _is_azure_auth_failure(exc: Exception) -> bool:
    return exc.__class__.__name__ == "ClientAuthenticationError"


def _is_azure_http_failure(exc: Exception) -> bool:
    return exc.__class__.__name__ == "HttpResponseError" or hasattr(exc, "status_code")


def main() -> int:
    """CLI entrypoint."""

    settings = get_settings()
    try:
        response = run_smoke()
    except LlmClientError as exc:
        cause = exc.__cause__ if isinstance(exc.__cause__, Exception) else exc
        if _is_azure_auth_failure(cause):
            print(f"LLM smoke test failed: Azure authentication failed. {exc}")
            print(troubleshooting_guidance())
            return 2
        if _is_azure_http_failure(cause):
            status_code = getattr(cause, "status_code", None)
            print(f"LLM smoke test failed: Azure OpenAI request failed. status_code={status_code}")
            print(troubleshooting_guidance())
            return 3
        print(f"LLM smoke test failed: {exc}")
        print(troubleshooting_guidance())
        return 4
    except Exception as exc:  # noqa: BLE001 - Azure SDKs expose environment-specific errors.
        if _is_azure_auth_failure(exc):
            print(f"LLM smoke test failed: Azure authentication failed. {exc}")
            print(troubleshooting_guidance())
            return 2
        if _is_azure_http_failure(exc):
            status_code = getattr(exc, "status_code", None)
            print(f"LLM smoke test failed: Azure OpenAI request failed. status_code={status_code}")
            print(troubleshooting_guidance())
            return 3
        raise

    print(
        format_success_summary(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            auth_mode=settings.AZURE_OPENAI_AUTH_MODE,
            response=response,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
