"""Tests for Docker build context safety rules."""

from __future__ import annotations

from pathlib import Path


def _dockerignore_lines() -> set[str]:
    return {
        line.strip()
        for line in Path(".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def test_dockerignore_excludes_secrets_and_generated_artifacts() -> None:
    lines = _dockerignore_lines()

    assert ".env" in lines
    assert ".env.*" in lines
    assert "data/raw" in lines
    assert "data/normalized" in lines
    assert "data/evidence" in lines
    assert "data/output" in lines


def test_dockerignore_does_not_exclude_langgraph_config() -> None:
    lines = _dockerignore_lines()

    assert "langgraph.json" not in lines
