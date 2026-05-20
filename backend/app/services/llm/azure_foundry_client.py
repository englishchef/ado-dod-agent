"""Azure OpenAI-compatible Foundry chat client using Entra ID auth."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any, Protocol

from backend.app.utils.config import Settings, get_settings

COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
SMOKE_PROMPT = 'Return only this JSON object and no other text: {"status":"ok"}'


class LlmClientError(RuntimeError):
    """Raised when local LLM smoke validation cannot be completed safely."""


class ChatModel(Protocol):
    """Minimal protocol for LangChain chat models used by this wrapper."""

    def invoke(self, input: str) -> Any:
        """Invoke the underlying chat model."""


class AzureFoundryChatClient:
    """Small Entra-only wrapper around LangChain AzureChatOpenAI."""

    def __init__(
        self,
        settings: Settings | None = None,
        model: ChatModel | None = None,
        credential_factory: Callable[[], Any] | None = None,
        token_provider_factory: Callable[[Any, str], Any] | None = None,
        model_factory: Callable[..., ChatModel] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._model = model
        self._credential_factory = credential_factory
        self._token_provider_factory = token_provider_factory
        self._model_factory = model_factory

    def invoke_text(self, prompt: str) -> str:
        """Invoke the configured chat model and return text content."""

        model = self._get_model()
        try:
            response = model.invoke(prompt)
        except Exception as exc:  # noqa: BLE001 - normalize provider-specific failures.
            raise LlmClientError(f"Model invocation failed: {exc}") from exc

        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(_extract_content_part(part) for part in content)
        raise LlmClientError(
            f"Model invocation returned unsupported response type: {type(content)}"
        )

    def invoke_json_smoke(self) -> dict[str, Any]:
        """Validate model access by requiring the model to return {"status": "ok"}."""

        raw_text = self.invoke_text(SMOKE_PROMPT)
        payload = _parse_json_object(raw_text)
        if payload.get("status") != "ok":
            raise LlmClientError('Response parse failure: expected status to equal "ok".')
        return payload

    def _get_model(self) -> ChatModel:
        if self._model is None:
            self._model = self._build_model()
        return self._model

    def _build_model(self) -> ChatModel:
        self._validate_settings()

        credential_factory = self._credential_factory
        token_provider_factory = self._token_provider_factory
        model_factory = self._model_factory

        if credential_factory is None or token_provider_factory is None:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            credential_factory = credential_factory or DefaultAzureCredential
            token_provider_factory = token_provider_factory or get_bearer_token_provider

        if model_factory is None:
            from langchain_openai import AzureChatOpenAI

            model_factory = AzureChatOpenAI

        credential = credential_factory()
        token_provider = token_provider_factory(credential, COGNITIVE_SERVICES_SCOPE)

        return model_factory(
            azure_endpoint=self._settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=self._settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=self._settings.AZURE_OPENAI_API_VERSION,
            azure_ad_token_provider=token_provider,
            temperature=self._settings.LLM_TEMPERATURE,
            max_completion_tokens=self._settings.LLM_MAX_TOKENS,
            timeout=self._settings.LLM_TIMEOUT_SECONDS,
        )

    def _validate_settings(self) -> None:
        if self._settings.AZURE_OPENAI_AUTH_MODE.lower() != "entra":
            raise LlmClientError(
                "Unsupported AZURE_OPENAI_AUTH_MODE. Phase 5A supports only 'entra'; "
                "API key auth is intentionally not implemented."
            )
        if not self._settings.AZURE_OPENAI_ENDPOINT:
            raise LlmClientError("Missing required setting: AZURE_OPENAI_ENDPOINT.")
        if _is_placeholder(self._settings.AZURE_OPENAI_ENDPOINT):
            raise LlmClientError(
                "AZURE_OPENAI_ENDPOINT still contains a placeholder value. "
                "Set it to the endpoint from the Azure AI Foundry/Azure OpenAI resource."
            )
        if not self._settings.AZURE_OPENAI_DEPLOYMENT:
            raise LlmClientError("Missing required setting: AZURE_OPENAI_DEPLOYMENT.")
        if _is_placeholder(self._settings.AZURE_OPENAI_DEPLOYMENT):
            raise LlmClientError(
                "AZURE_OPENAI_DEPLOYMENT still contains a placeholder value. "
                "Set it to the deployed model name from the Azure portal."
            )
        if not self._settings.AZURE_OPENAI_API_VERSION:
            raise LlmClientError("Missing required setting: AZURE_OPENAI_API_VERSION.")
        if _is_placeholder(self._settings.AZURE_OPENAI_API_VERSION):
            raise LlmClientError(
                "AZURE_OPENAI_API_VERSION still contains a placeholder value. "
                "Set it to an API version supported by the configured endpoint."
            )


def _extract_content_part(part: Any) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        value = part.get("text") or part.get("content") or ""
        return value if isinstance(value, str) else ""
    text = getattr(part, "text", "")
    return text if isinstance(text, str) else ""


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        "<" in normalized
        or ">" in normalized
        or normalized.startswith("your-")
        or "://your-" in normalized
        or ".your-" in normalized
    )


def _parse_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmClientError("Response parse failure: model did not return valid JSON.") from exc

    if not isinstance(payload, dict):
        raise LlmClientError("Response parse failure: model response JSON was not an object.")
    return payload
