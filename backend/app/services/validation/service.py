"""Phase 6 validation, assembly, and confidence orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from backend.app.models.llm_outputs import CombinedLlmOutputs
from backend.app.models.validated_outputs import (
    ServiceNowPayload,
    ValidatedDodOutput,
    ValidationIssue,
)
from backend.app.services.formatting.servicenow_formatter import (
    SERVICE_NOW_FIELD_NAMES,
    build_traceability_report,
    clean_servicenow_field_text,
    format_service_now_payload,
)
from backend.app.services.scoring.confidence import score_confidence
from backend.app.services.validation.output_repair import repair_llm_output_shape
from backend.app.services.validation.output_validator import (
    validate_llm_outputs,
    validate_service_now_payload,
)
from backend.app.services.validation.payload_assembler import assemble_service_now_payload


def validate_and_assemble_outputs(
    build_id: int,
    llm_outputs: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_llm_outputs_path: str | None = None,
    source_evidence_bundle_path: str | None = None,
    allow_llm_repair: bool = False,
) -> ValidatedDodOutput:
    """Validate Phase 5B outputs and assemble final ServiceNow-ready payload."""

    _ = allow_llm_repair
    repaired_payload = _repair_combined_payload(llm_outputs)
    parsed_outputs = CombinedLlmOutputs.model_validate(repaired_payload)
    bucket_results = validate_llm_outputs(parsed_outputs, evidence_bundle)
    validation_issues = [issue for result in bucket_results for issue in result.issues]
    try:
        assembled_payload = assemble_service_now_payload(parsed_outputs)
    except ValidationError as exc:
        assembled_payload = _construct_unchecked_payload(parsed_outputs)
        validation_issues.extend(_issues_from_payload_validation_error(exc))
    try:
        service_now_payload = format_service_now_payload(assembled_payload)
    except ValidationError as exc:
        service_now_payload = _construct_cleaned_payload(assembled_payload)
        validation_issues.extend(_issues_from_payload_validation_error(exc))
    validation_issues.extend(validate_service_now_payload(service_now_payload, evidence_bundle))
    confidence = score_confidence(parsed_outputs, evidence_bundle, validation_issues)
    traceability_report = build_traceability_report(
        build_id=build_id,
        llm_outputs=parsed_outputs.model_dump(mode="json"),
        evidence_bundle=evidence_bundle,
        source_llm_outputs_path=source_llm_outputs_path,
        source_evidence_bundle_path=source_evidence_bundle_path,
    )

    return ValidatedDodOutput(
        build_id=build_id,
        generated_at=datetime.now(UTC),
        is_valid=not any(issue.severity == "error" for issue in validation_issues),
        service_now_payload=service_now_payload,
        bucket_validation_results=bucket_results,
        confidence=confidence,
        validation_issues=validation_issues,
        source_llm_outputs_path=source_llm_outputs_path,
        source_evidence_bundle_path=source_evidence_bundle_path,
        traceability_report=traceability_report,
    )


def _repair_combined_payload(payload: dict[str, Any]) -> dict[str, Any]:
    repaired = dict(payload)
    for bucket in ("bucket_1", "bucket_2", "bucket_3"):
        value = repaired.get(bucket)
        if isinstance(value, dict):
            repaired[bucket] = repair_llm_output_shape(value)
    try:
        CombinedLlmOutputs.model_validate(repaired)
    except ValidationError:
        raise
    return repaired


def _construct_unchecked_payload(llm_outputs: CombinedLlmOutputs) -> ServiceNowPayload:
    payload = llm_outputs.model_dump(mode="json")
    return ServiceNowPayload.model_construct(
        change_description=payload.get("bucket_1", {}).get("change_description", ""),
        short_change_description=payload.get("bucket_1", {}).get("short_change_description", ""),
        justification=payload.get("bucket_1", {}).get("justification", ""),
        testing_performed=payload.get("bucket_2", {}).get("testing_performed", ""),
        implementation_plan=payload.get("bucket_2", {}).get("implementation_plan", ""),
        validation_plan=payload.get("bucket_2", {}).get("validation_plan", ""),
        backout_plan=payload.get("bucket_3", {}).get("backout_plan", ""),
        risk_impact_analysis=payload.get("bucket_3", {}).get("risk_impact_analysis", ""),
    )


def _construct_cleaned_payload(payload: ServiceNowPayload) -> ServiceNowPayload:
    raw_payload = payload.model_dump()
    cleaned = {
        field: clean_servicenow_field_text(str(raw_payload.get(field, "")))
        for field in SERVICE_NOW_FIELD_NAMES
    }
    return ServiceNowPayload.model_construct(
        change_description=cleaned["change_description"],
        short_change_description=cleaned["short_change_description"],
        justification=cleaned["justification"],
        testing_performed=cleaned["testing_performed"],
        implementation_plan=cleaned["implementation_plan"],
        validation_plan=cleaned["validation_plan"],
        backout_plan=cleaned["backout_plan"],
        risk_impact_analysis=cleaned["risk_impact_analysis"],
    )


def _issues_from_payload_validation_error(exc: ValidationError) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for error in exc.errors():
        field = str(error.get("loc", ["unknown"])[0])
        issues.append(
            ValidationIssue(
                severity="error",
                code="invalid_service_now_field",
                message=str(error["msg"]),
                field=field,
                bucket=None,
            )
        )
    return issues
