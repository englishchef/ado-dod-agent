"""Tests for LangGraph invocation script API-key behavior."""

from __future__ import annotations

from typing import Any

from scripts import invoke_dod_langgraph


def test_invoke_dod_langgraph_help_works_without_keyvault(capsys: Any) -> None:
    try:
        invoke_dod_langgraph.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "Invoke the LangGraph DoD assistant" in capsys.readouterr().out
