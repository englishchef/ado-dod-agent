"""Assemble flat ServiceNow payloads from Phase 5B bucket outputs."""

from __future__ import annotations

from typing import Any

from backend.app.models.llm_outputs import CombinedLlmOutputs
from backend.app.models.validated_outputs import ServiceNowPayload
from backend.app.services.formatting.servicenow_formatter import format_service_now_payload

SERVICE_NOW_FIELDS = (
    "change_description",
    "short_change_description",
    "justification",
    "testing_performed",
    "implementation_plan",
    "validation_plan",
    "backout_plan",
    "risk_impact_analysis",
)


def assemble_service_now_payload(
    llm_outputs: CombinedLlmOutputs | dict[str, Any],
) -> ServiceNowPayload:
    """Combine bucket outputs into exactly eight ServiceNow fields."""

    payload = llm_outputs.model_dump(mode="json") if isinstance(
        llm_outputs, CombinedLlmOutputs
    ) else llm_outputs
    assembled = {
        "change_description": payload.get("bucket_1", {}).get("change_description"),
        "short_change_description": payload.get("bucket_1", {}).get("short_change_description"),
        "justification": payload.get("bucket_1", {}).get("justification"),
        "testing_performed": payload.get("bucket_2", {}).get("testing_performed"),
        "implementation_plan": payload.get("bucket_2", {}).get("implementation_plan"),
        "validation_plan": payload.get("bucket_2", {}).get("validation_plan"),
        "backout_plan": payload.get("bucket_3", {}).get("backout_plan"),
        "risk_impact_analysis": payload.get("bucket_3", {}).get("risk_impact_analysis"),
    }
    return format_service_now_payload(ServiceNowPayload.model_validate(assembled))
