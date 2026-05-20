"""Tests for the Azure Foundry LLM client wrapper."""

from __future__ import annotations

from typing import Any

from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
from backend.app.utils.config import Settings
from pytest import raises


class DummyResponse:
    def __init__(self, content: Any) -> None:
        self.content = content


class DummyModel:
    def __init__(self, content: Any = '{"status":"ok"}', failure: Exception | None = None) -> None:
        self.content = content
        self.failure = failure

    def invoke(self, input: str) -> DummyResponse:
        _ = input
        if self.failure:
            raise self.failure
        return DummyResponse(self.content)


def valid_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT": "dod-smoke",
        "AZURE_OPENAI_API_VERSION": "2024-10-21",
        "AZURE_OPENAI_AUTH_MODE": "entra",
    }
    values.update(overrides)
    return Settings(**values)


def test_client_raises_error_when_endpoint_missing() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(AZURE_OPENAI_ENDPOINT=None))

    with raises(LlmClientError, match="AZURE_OPENAI_ENDPOINT"):
        client.invoke_text("test")


def test_client_raises_error_when_deployment_missing() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(AZURE_OPENAI_DEPLOYMENT=None))

    with raises(LlmClientError, match="AZURE_OPENAI_DEPLOYMENT"):
        client.invoke_text("test")


def test_client_raises_error_when_api_version_missing() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(AZURE_OPENAI_API_VERSION=None))

    with raises(LlmClientError, match="AZURE_OPENAI_API_VERSION"):
        client.invoke_text("test")


def test_client_rejects_non_entra_auth_mode() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(AZURE_OPENAI_AUTH_MODE="api_key"))

    with raises(LlmClientError, match="supports only 'entra'"):
        client.invoke_text("test")


def test_client_rejects_placeholder_endpoint() -> None:
    client = AzureFoundryChatClient(
        settings=valid_settings(AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/")
    )

    with raises(LlmClientError, match="placeholder"):
        client.invoke_text("test")


def test_client_rejects_placeholder_deployment() -> None:
    client = AzureFoundryChatClient(
        settings=valid_settings(AZURE_OPENAI_DEPLOYMENT="your-deployment-name")
    )

    with raises(LlmClientError, match="placeholder"):
        client.invoke_text("test")


def test_client_parses_status_ok_json() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(), model=DummyModel('{"status":"ok"}'))

    assert client.invoke_json_smoke() == {"status": "ok"}


def test_client_parses_markdown_wrapped_json() -> None:
    client = AzureFoundryChatClient(
        settings=valid_settings(),
        model=DummyModel('```json\n{"status":"ok"}\n```'),
    )

    assert client.invoke_json_smoke() == {"status": "ok"}


def test_client_raises_parse_error_for_invalid_json() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(), model=DummyModel("not-json"))

    with raises(LlmClientError, match="valid JSON"):
        client.invoke_json_smoke()


def test_client_raises_error_for_non_ok_status() -> None:
    client = AzureFoundryChatClient(settings=valid_settings(), model=DummyModel('{"status":"no"}'))

    with raises(LlmClientError, match="status"):
        client.invoke_json_smoke()
