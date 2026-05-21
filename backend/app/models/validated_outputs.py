"""Validated Phase 6 ServiceNow-ready output models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PLACEHOLDER_VALUES = {
    "tbd",
    "n/a",
    "none",
    "not available",
    "to be determined",
    "placeholder",
}


class ValidatedOutputBaseModel(BaseModel):
    """Base config for validated output payloads."""

    model_config = ConfigDict(extra="forbid")


class ValidationIssue(ValidatedOutputBaseModel):
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    field: str | None = None
    bucket: str | None = None


class ServiceNowPayload(ValidatedOutputBaseModel):
    change_description: str
    short_change_description: str
    justification: str
    testing_performed: str
    implementation_plan: str
    validation_plan: str
    backout_plan: str
    risk_impact_analysis: str

    @field_validator("*")
    @classmethod
    def service_now_fields_must_be_real_text(cls, value: str) -> str:
        text = value.strip()
        if text == "":
            raise ValueError("ServiceNow field must not be empty")
        if text.lower() in PLACEHOLDER_VALUES:
            raise ValueError("ServiceNow field contains placeholder text")
        return value


class BucketValidationResult(ValidatedOutputBaseModel):
    bucket_name: str
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    repaired: bool = False
    repair_notes: list[str] = Field(default_factory=list)


class ConfidenceScore(ValidatedOutputBaseModel):
    overall: float = Field(ge=0, le=1)
    bucket_1: float = Field(ge=0, le=1)
    bucket_2: float = Field(ge=0, le=1)
    bucket_3: float = Field(ge=0, le=1)
    rationale: dict[str, list[str]]


class ValidatedDodOutput(ValidatedOutputBaseModel):
    schema_version: str = "1.0"
    build_id: int
    generated_at: datetime
    is_valid: bool
    service_now_payload: ServiceNowPayload
    bucket_validation_results: list[BucketValidationResult]
    confidence: ConfidenceScore
    validation_issues: list[ValidationIssue]
    source_llm_outputs_path: str | None = None
    source_evidence_bundle_path: str | None = None
