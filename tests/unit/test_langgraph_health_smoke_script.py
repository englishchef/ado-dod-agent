"""Tests for the deployed LangGraph /ok health smoke script."""

from __future__ import annotations

from typing import Any

from scripts import smoke_langgraph_health


def test_health_help_works_without_network(capsys: Any) -> None:
    try:
        smoke_langgraph_health.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "Validate deployed LangGraph /ok health" in capsys.readouterr().out


def test_health_url_builder_appends_ok() -> None:
    assert (
        smoke_langgraph_health.build_health_url("https://langgraph.example")
        == "https://langgraph.example/ok"
    )
    assert (
        smoke_langgraph_health.build_health_url("https://langgraph.example/base/")
        == "https://langgraph.example/base/ok"
    )
    assert (
        smoke_langgraph_health.build_health_url("https://langgraph.example/ok")
        == "https://langgraph.example/ok"
    )


def test_api_key_header_is_not_printed(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("LANGGRAPH_API_KEY", "super-secret-value")

    def fake_check_health(**kwargs: Any) -> tuple[int, str]:
        assert kwargs["headers"] == {"x-api-key": "super-secret-value"}
        return 200, "ok"

    monkeypatch.setattr(smoke_langgraph_health, "check_health", fake_check_health)

    assert (
        smoke_langgraph_health.main(
            [
                "--url",
                "https://langgraph.example",
                "--api-key-env",
                "LANGGRAPH_API_KEY",
                "--api-key-header",
                "x-api-key",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "super-secret-value" not in output
    assert "api_key_printed: false" in output


def test_key_vault_api_key_header_defaults_to_x_api_key(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        smoke_langgraph_health,
        "get_langgraph_api_key",
        lambda **_: "key-value",
    )

    headers = smoke_langgraph_health.build_key_vault_headers(
        environ={
            "LANGGRAPH_KEY_VAULT_URL": "https://vault.example/",
            "LANGGRAPH_KEY_VAULT_SECRET_NAME": "secret-name",
        }
    )

    assert headers == {"x-api-key": "key-value"}


def test_key_vault_api_key_header_respects_config(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        smoke_langgraph_health,
        "get_langgraph_api_key",
        lambda **_: "key-value",
    )

    headers = smoke_langgraph_health.build_key_vault_headers(
        environ={
            "LANGGRAPH_API_KEY_HEADER": "x-custom-key",
            "LANGGRAPH_KEY_VAULT_URL": "https://vault.example/",
            "LANGGRAPH_KEY_VAULT_SECRET_NAME": "secret-name",
        }
    )

    assert headers == {"x-custom-key": "key-value"}
