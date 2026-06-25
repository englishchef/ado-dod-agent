"""Tests for static enterprise pipeline config validation."""

from __future__ import annotations

from pathlib import Path

from scripts.smoke_pipeline_config import validate_pipeline_config


def _write_pipeline(root: Path, service_text: str, vars_text: str) -> None:
    pipeline_root = root / ".pipelines"
    (pipeline_root / "config" / "dev").mkdir(parents=True)
    (pipeline_root / "service_build_deploy.yml").write_text(service_text, encoding="utf-8")
    (pipeline_root / "config" / "dev" / "vars.yml").write_text(vars_text, encoding="utf-8")
    (pipeline_root / "config" / "global-vars.yml").write_text(vars_text, encoding="utf-8")


def test_pipeline_config_skips_when_pipelines_folder_absent(tmp_path: Path) -> None:
    result = validate_pipeline_config(tmp_path)

    assert result.ok
    assert result.skipped


def test_pipeline_config_identifies_langchain_agent_template(tmp_path: Path) -> None:
    _write_pipeline(
        tmp_path,
        """
        extends:
          template: /common-libs/az-langchain-agent.yml@cicd_moderndeployment
        parameters:
          dockerFile: Dockerfile
          imageRepository: dod-agent
        """,
        """
        LANGGRAPH_ASSISTANT_ID: dod
        AGENT_CONFIG_KEY_VAULT_URL: $(agentConfigKeyVaultUrl)
        AGENT_CONFIG_SECRET_NAME: $(agentConfigSecretName)
        """,
    )

    result = validate_pipeline_config(tmp_path)

    assert result.ok
    assert "az-langchain-agent template" in result.configured
    assert "LANGGRAPH_ASSISTANT_ID=dod" in result.configured


def test_pipeline_config_flags_container_apps_template(tmp_path: Path) -> None:
    _write_pipeline(
        tmp_path,
        """
        extends:
          template: /common-libs/az-langchain-agent.yml@cicd_moderndeployment
        steps:
          - template: container-app-deploy.yml
        """,
        """
        LANGGRAPH_ASSISTANT_ID: dod
        AGENT_CONFIG_KEY_VAULT_URL: $(agentConfigKeyVaultUrl)
        AGENT_CONFIG_SECRET_NAME: $(agentConfigSecretName)
        """,
    )

    result = validate_pipeline_config(tmp_path)

    assert not result.ok
    assert any("Container Apps" in error for error in result.errors)
