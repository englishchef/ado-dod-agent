"""Static validation for the DoD enterprise pipeline configuration."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

LANGCHAIN_AGENT_TEMPLATE = "/common-libs/az-langchain-agent.yml"
CONTAINER_APPS_MARKERS = {
    "container-app",
    "containerapp",
    "az-container-app",
    "container_apps",
}
SECRET_KEY_MARKERS = {
    "password",
    "secret:",
    "api_key:",
    "apikey:",
    "token:",
    "cosmos_key:",
    "client_secret:",
}


@dataclass
class PipelineConfigValidation:
    """Safe static validation result for the .pipelines folder."""

    root: Path
    skipped: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    configured: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_pipeline_config(
    root: Path = Path("."),
    *,
    strict: bool = False,
) -> PipelineConfigValidation:
    """Validate enterprise pipeline files without running Azure DevOps or Azure."""

    pipelines_root = root / ".pipelines"
    result = PipelineConfigValidation(root=pipelines_root)
    if not pipelines_root.exists():
        result.skipped = True
        result.warnings.append(".pipelines folder not present; static validation skipped.")
        return result

    service_file = pipelines_root / "service_build_deploy.yml"
    dev_vars = pipelines_root / "config" / "dev" / "vars.yml"
    global_vars = pipelines_root / "config" / "global-vars.yml"
    _require_file(result, service_file, ".pipelines/service_build_deploy.yml")
    _require_file(result, dev_vars, ".pipelines/config/dev/vars.yml")
    _require_file(result, global_vars, ".pipelines/config/global-vars.yml")

    if service_file.exists():
        service_text = _read_text(service_file)
        if LANGCHAIN_AGENT_TEMPLATE not in service_text:
            result.errors.append(
                "service_build_deploy.yml must reference /common-libs/az-langchain-agent.yml."
            )
        else:
            result.configured.append("az-langchain-agent template")
        if _contains_container_apps_reference(service_text):
            result.errors.append("DoD pipeline must not reference Container Apps deployment.")
        if "Dockerfile" in service_text:
            result.configured.append("Dockerfile")
        else:
            result.warnings.append("Dockerfile was not referenced explicitly.")
        _validate_no_hardcoded_secrets(result, service_text, service_file)
        _validate_required_name_hint(result, service_text, "image")
        _validate_required_name_hint(result, service_text, "repository")

    for vars_file in (dev_vars, global_vars):
        if not vars_file.exists():
            continue
        text = _read_text(vars_file)
        _validate_no_hardcoded_secrets(result, text, vars_file)
        _validate_assistant_id(result, text, strict=strict)
        _validate_config_pointer(result, text, strict=strict)

    return result


def render_pipeline_config_summary(result: PipelineConfigValidation) -> str:
    """Render a safe pipeline validation summary."""

    status = "skipped" if result.skipped else ("ok" if result.ok else "invalid")
    lines = [
        "Pipeline config static validation",
        f"- path: {result.root}",
        f"- status: {status}",
    ]
    if result.configured:
        lines.append("- configured: " + ", ".join(sorted(set(result.configured))))
    if result.warnings:
        lines.append("- warnings:")
        lines.extend(f"  - {item}" for item in result.warnings)
    if result.errors:
        lines.append("- errors:")
        lines.extend(f"  - {item}" for item in result.errors)
    lines.append("Secret values are intentionally not printed.")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Statically validate DoD pipeline config.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = validate_pipeline_config(args.root, strict=args.strict)
    print(render_pipeline_config_summary(result))
    return 0 if result.ok else 2


def _require_file(result: PipelineConfigValidation, path: Path, label: str) -> None:
    if path.exists():
        result.configured.append(label)
    else:
        result.errors.append(f"{label} is required when .pipelines is present.")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _contains_container_apps_reference(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in CONTAINER_APPS_MARKERS)


def _validate_no_hardcoded_secrets(
    result: PipelineConfigValidation,
    text: str,
    path: Path,
) -> None:
    lowered = text.lower()
    for marker in SECRET_KEY_MARKERS:
        if marker in lowered and "$(" not in text:
            result.errors.append(f"{path} appears to contain a hardcoded secret-like key.")
            return


def _validate_assistant_id(
    result: PipelineConfigValidation,
    text: str,
    *,
    strict: bool,
) -> None:
    if "LANGGRAPH_ASSISTANT_ID" not in text:
        return
    compact = text.replace('"', "").replace("'", "")
    if "LANGGRAPH_ASSISTANT_ID" in compact and "dod" in compact:
        result.configured.append("LANGGRAPH_ASSISTANT_ID=dod")
        return
    message = "LANGGRAPH_ASSISTANT_ID should be dod for the DoD agent."
    if strict:
        result.errors.append(message)
    else:
        result.warnings.append(message)


def _validate_config_pointer(
    result: PipelineConfigValidation,
    text: str,
    *,
    strict: bool,
) -> None:
    missing = [
        name
        for name in ("AGENT_CONFIG_KEY_VAULT_URL", "AGENT_CONFIG_SECRET_NAME")
        if name not in text
    ]
    if not missing:
        result.configured.append("agent config Key Vault pointer")
        return
    message = (
        "Agent config Key Vault pointer is not present in vars.yml; it must be "
        "provided by environment or variable group."
    )
    if strict:
        result.errors.append(message)
    else:
        result.warnings.append(message)


def _validate_required_name_hint(
    result: PipelineConfigValidation,
    text: str,
    hint: str,
) -> None:
    if hint in text.lower():
        result.configured.append(f"{hint} name")
    else:
        result.warnings.append(f"No obvious {hint} name found in service pipeline config.")


if __name__ == "__main__":
    raise SystemExit(main())
