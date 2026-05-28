"""Pydantic models for Phase 5B generated ServiceNow field drafts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LlmOutputBaseModel(BaseModel):
    """Base config for generated LLM output models."""

    model_config = ConfigDict(extra="ignore")


class Bucket1GeneratedOutput(LlmOutputBaseModel):
    target_fields: list[str] = Field(
        default_factory=lambda: [
            "change_description",
            "short_change_description",
            "justification",
        ]
    )
    change_description: str
    short_change_description: str
    justification: str
    evidence_used: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    model_confidence: float = Field(ge=0, le=1)
    generation_notes: list[str] = Field(default_factory=list)

    @field_validator("change_description", "short_change_description", "justification")
    @classmethod
    def strings_must_not_be_empty(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("generated text fields must not be empty")
        return value

    @model_validator(mode="after")
    def add_short_description_note(self) -> Bucket1GeneratedOutput:
        if len(self.short_change_description) > 160:
            note = "short_change_description exceeds 160 characters; review for ServiceNow fit."
            if note not in self.generation_notes:
                self.generation_notes.append(note)
        return self


class Bucket2GeneratedOutput(LlmOutputBaseModel):
    target_fields: list[str] = Field(
        default_factory=lambda: [
            "testing_performed",
            "implementation_plan",
            "validation_plan",
        ]
    )
    testing_performed: str
    implementation_plan: str
    validation_plan: str
    evidence_used: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    model_confidence: float = Field(ge=0, le=1)
    generation_notes: list[str] = Field(default_factory=list)

    @field_validator("testing_performed", "implementation_plan", "validation_plan")
    @classmethod
    def strings_must_not_be_empty(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("generated text fields must not be empty")
        return value


class Bucket3GeneratedOutput(LlmOutputBaseModel):
    target_fields: list[str] = Field(
        default_factory=lambda: [
            "backout_plan",
            "risk_impact_analysis",
        ]
    )
    backout_plan: str
    risk_impact_analysis: str
    evidence_used: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    model_confidence: float = Field(ge=0, le=1)
    generation_notes: list[str] = Field(default_factory=list)

    @field_validator("backout_plan", "risk_impact_analysis")
    @classmethod
    def strings_must_not_be_empty(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("generated text fields must not be empty")
        return value


class LlmModelMetadata(LlmOutputBaseModel):
    provider: str
    deployment: str | None
    api_version: str | None
    auth_mode: str
    prompt_versions: dict[str, str]
    prompt_strategies: dict[str, str] = Field(default_factory=dict)


class CombinedLlmOutputs(LlmOutputBaseModel):
    schema_version: str = "1.0"
    build_id: int
    organization: str | None = None
    project: str | None = None
    generated_at: datetime
    source_evidence_bundle_path: str | None = None
    model_metadata: LlmModelMetadata
    bucket_1: Bucket1GeneratedOutput
    bucket_2: Bucket2GeneratedOutput
    bucket_3: Bucket3GeneratedOutput
