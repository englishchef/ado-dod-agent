"""Tests for runtime identity and docs examples."""

from __future__ import annotations

from pathlib import Path


def test_enterprise_docs_contain_runtime_identity_contract() -> None:
    text = Path("docs/enterprise-runtime-config.md").read_text(encoding="utf-8")

    assert "Runtime Identity And Permissions" in text
    assert "pipeline permissions and runtime permissions are not the same thing" in text
    assert "/ok health check does not prove Cosmos write permission" in text


def test_docs_examples_do_not_include_real_secret_values() -> None:
    for path in (
        Path("docs/enterprise-runtime-config.md"),
        Path("docs/key-vault-config-contract.md"),
        Path("docs/post-deploy-validation.md"),
    ):
        text = path.read_text(encoding="utf-8").lower()
        assert "super-secret" not in text
        assert "replace-with-secret" not in text
        assert "cosmos_key" not in text or "<" in text or "should not" in text
