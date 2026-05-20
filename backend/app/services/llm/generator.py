"""Phase 5B ServiceNow field generation from deterministic evidence buckets."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from backend.app.models.llm_outputs import (
    Bucket1GeneratedOutput,
    Bucket2GeneratedOutput,
    Bucket3GeneratedOutput,
    CombinedLlmOutputs,
    LlmModelMetadata,
)
from backend.app.prompts import (
    bucket_1_change_intent,
    bucket_2_execution_validation,
    bucket_3_rollback_risk,
)
from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
from backend.app.services.llm.json_parser import extract_json_object
from backend.app.utils.config import get_settings


def generate_bucket_1(
    evidence: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
) -> Bucket1GeneratedOutput:
    prompt = bucket_1_change_intent.build_prompt(evidence)
    return _generate_bucket(prompt, Bucket1GeneratedOutput, client)


def generate_bucket_2(
    evidence: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
) -> Bucket2GeneratedOutput:
    prompt = bucket_2_execution_validation.build_prompt(evidence)
    return _generate_bucket(prompt, Bucket2GeneratedOutput, client)


def generate_bucket_3(
    evidence: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
) -> Bucket3GeneratedOutput:
    prompt = bucket_3_rollback_risk.build_prompt(evidence)
    return _generate_bucket(prompt, Bucket3GeneratedOutput, client)


def generate_all_buckets(
    build_id: int,
    evidence_bundle: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
    source_path: str | None = None,
) -> CombinedLlmOutputs:
    """Generate all eight ServiceNow draft fields from evidence bucket inputs."""

    resolved_client = client or AzureFoundryChatClient()
    bucket_1_evidence = _require_bucket(evidence_bundle, "bucket_1")
    bucket_2_evidence = _require_bucket(evidence_bundle, "bucket_2")
    bucket_3_evidence = _require_bucket(evidence_bundle, "bucket_3")

    bucket_1 = generate_bucket_1(bucket_1_evidence, resolved_client)
    bucket_2 = generate_bucket_2(bucket_2_evidence, resolved_client)
    bucket_3 = generate_bucket_3(bucket_3_evidence, resolved_client)

    settings = get_settings()
    return CombinedLlmOutputs(
        build_id=build_id,
        organization=_optional_str(evidence_bundle.get("organization")),
        project=_optional_str(evidence_bundle.get("project")),
        generated_at=datetime.now(UTC),
        source_evidence_bundle_path=source_path,
        model_metadata=LlmModelMetadata(
            provider="azure_openai",
            deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            auth_mode=settings.AZURE_OPENAI_AUTH_MODE,
            prompt_versions={
                "bucket_1": bucket_1_change_intent.PROMPT_VERSION,
                "bucket_2": bucket_2_execution_validation.PROMPT_VERSION,
                "bucket_3": bucket_3_rollback_risk.PROMPT_VERSION,
            },
        ),
        bucket_1=bucket_1,
        bucket_2=bucket_2,
        bucket_3=bucket_3,
    )


def _generate_bucket[TGeneratedOutput: BaseModel](
    prompt: str,
    output_model: type[TGeneratedOutput],
    client: AzureFoundryChatClient | None,
) -> TGeneratedOutput:
    resolved_client = client or AzureFoundryChatClient()
    raw_text = resolved_client.invoke_text(prompt)
    payload = extract_json_object(raw_text)
    try:
        return output_model.model_validate(payload)
    except ValidationError as exc:
        raise LlmClientError(f"Model output failed schema validation: {exc}") from exc


def _require_bucket(evidence_bundle: dict[str, Any], key: str) -> dict[str, Any]:
    payload = evidence_bundle.get(key)
    if not isinstance(payload, dict):
        raise LlmClientError(f"Evidence bundle is missing required JSON object: {key}.")
    return payload


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
