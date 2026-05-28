"""Phase 5B ServiceNow field generation from deterministic evidence buckets."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from backend.app.models.llm_outputs import (
    Bucket1GeneratedOutput,
    Bucket2GeneratedOutput,
    Bucket3GeneratedOutput,
    CombinedLlmOutputs,
    LlmModelMetadata,
)
from backend.app.models.routing import PromptStrategySelection
from backend.app.prompts import (
    bucket_1_change_intent,
    bucket_2_execution_validation,
    bucket_3_rollback_risk,
)
from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
from backend.app.services.llm.json_parser import extract_json_object
from backend.app.utils.config import get_settings

TGeneratedOutput = TypeVar("TGeneratedOutput", bound=BaseModel)
TBucketOutput = TypeVar("TBucketOutput", bound=BaseModel)


def generate_bucket_1(
    evidence: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
    prompt_strategy: str | None = None,
) -> Bucket1GeneratedOutput:
    prompt = bucket_1_change_intent.build_prompt(evidence, prompt_strategy=prompt_strategy)
    return _generate_bucket(prompt, Bucket1GeneratedOutput, client)


def generate_bucket_2(
    evidence: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
    prompt_strategy: str | None = None,
) -> Bucket2GeneratedOutput:
    prompt = bucket_2_execution_validation.build_prompt(evidence, prompt_strategy=prompt_strategy)
    return _generate_bucket(prompt, Bucket2GeneratedOutput, client)


def generate_bucket_3(
    evidence: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
    prompt_strategy: str | None = None,
) -> Bucket3GeneratedOutput:
    prompt = bucket_3_rollback_risk.build_prompt(evidence, prompt_strategy=prompt_strategy)
    return _generate_bucket(prompt, Bucket3GeneratedOutput, client)


def generate_all_buckets(
    build_id: int,
    evidence_bundle: dict[str, Any],
    client: AzureFoundryChatClient | None = None,
    source_path: str | None = None,
    prompt_strategy_selection: PromptStrategySelection | dict[str, Any] | None = None,
    max_retries_per_bucket: int = 1,
    on_bucket_retry: Callable[[str, int, Exception], None] | None = None,
) -> CombinedLlmOutputs:
    """Generate all eight ServiceNow draft fields from evidence bucket inputs."""

    resolved_client = client or AzureFoundryChatClient()
    bucket_1_evidence = _require_bucket(evidence_bundle, "bucket_1")
    bucket_2_evidence = _require_bucket(evidence_bundle, "bucket_2")
    bucket_3_evidence = _require_bucket(evidence_bundle, "bucket_3")
    strategies = _resolve_prompt_strategies(prompt_strategy_selection)

    bucket_1 = _generate_bucket_with_retry(
        "bucket_1",
        lambda: generate_bucket_1(
            bucket_1_evidence,
            resolved_client,
            prompt_strategy=strategies["bucket_1"],
        ),
        max_retries_per_bucket,
        on_bucket_retry,
    )
    bucket_2 = _generate_bucket_with_retry(
        "bucket_2",
        lambda: generate_bucket_2(
            bucket_2_evidence,
            resolved_client,
            prompt_strategy=strategies["bucket_2"],
        ),
        max_retries_per_bucket,
        on_bucket_retry,
    )
    bucket_3 = _generate_bucket_with_retry(
        "bucket_3",
        lambda: generate_bucket_3(
            bucket_3_evidence,
            resolved_client,
            prompt_strategy=strategies["bucket_3"],
        ),
        max_retries_per_bucket,
        on_bucket_retry,
    )

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
            prompt_strategies=strategies,
        ),
        bucket_1=bucket_1,
        bucket_2=bucket_2,
        bucket_3=bucket_3,
    )


def _generate_bucket(
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


def _generate_bucket_with_retry(
    bucket_name: str,
    generate: Callable[[], TBucketOutput],
    max_retries: int,
    on_retry: Callable[[str, int, Exception], None] | None = None,
) -> TBucketOutput:
    attempts = max(0, int(max_retries)) + 1
    last_error: Exception | None = None
    for index in range(attempts):
        try:
            return generate()
        except Exception as exc:
            last_error = exc
            if index < attempts - 1 and on_retry is not None:
                on_retry(bucket_name, index + 1, exc)
    raise LlmClientError(
        f"{bucket_name} generation failed after retry: {last_error}"
    ) from last_error


def _resolve_prompt_strategies(
    selection: PromptStrategySelection | dict[str, Any] | None,
) -> dict[str, str]:
    defaults = {
        "bucket_1": "bucket_1_standard",
        "bucket_2": "bucket_2_standard",
        "bucket_3": "bucket_3_standard",
    }
    if selection is None:
        return defaults
    payload = (
        selection.model_dump() if isinstance(selection, PromptStrategySelection) else selection
    )
    return {
        "bucket_1": _optional_str(payload.get("bucket_1_strategy")) or defaults["bucket_1"],
        "bucket_2": _optional_str(payload.get("bucket_2_strategy")) or defaults["bucket_2"],
        "bucket_3": _optional_str(payload.get("bucket_3_strategy")) or defaults["bucket_3"],
    }


def _require_bucket(evidence_bundle: dict[str, Any], key: str) -> dict[str, Any]:
    payload = evidence_bundle.get(key)
    if not isinstance(payload, dict):
        raise LlmClientError(f"Evidence bundle is missing required JSON object: {key}.")
    return payload


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None
