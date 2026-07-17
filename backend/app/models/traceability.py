"""Traceability report models for ServiceNow payload generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TraceabilityBaseModel(BaseModel):
    """Base config for traceability payloads."""

    model_config = ConfigDict(extra="forbid")


class FieldTraceability(TraceabilityBaseModel):
    field_name: str
    evidence_used: list[str] = Field(default_factory=list)
    friendly_refs: list[str] = Field(default_factory=list)
    original_refs: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TraceabilityReport(TraceabilityBaseModel):
    schema_version: str = "1.0"
    build_id: int
    generated_at: datetime
    source_llm_outputs_path: str | None = None
    source_evidence_bundle_path: str | None = None
    field_traceability: dict[str, FieldTraceability] = Field(default_factory=dict)
    environment_candidates: list[dict[str, Any]] = Field(default_factory=list)
    backout_time_derivation: dict[str, Any] | None = None
    rejected_stages: list[dict[str, Any]] = Field(default_factory=list)
    deployment_activities_used: list[dict[str, Any]] = Field(default_factory=list)
    application_resolution: dict[str, Any] | None = None
    source_ref_map: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
