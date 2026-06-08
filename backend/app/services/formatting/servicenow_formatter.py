"""Deterministic ServiceNow payload formatting and traceability reporting."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from backend.app.models.traceability import FieldTraceability, TraceabilityReport
from backend.app.models.validated_outputs import ServiceNowPayload

SERVICE_NOW_FIELD_NAMES = (
    "change_description",
    "short_change_description",
    "justification",
    "testing_performed",
    "implementation_plan",
    "validation_plan",
    "backout_plan",
    "risk_impact_analysis",
)

BUCKET_FIELD_MAP = {
    "bucket_1": ("change_description", "short_change_description", "justification"),
    "bucket_2": ("testing_performed", "implementation_plan", "validation_plan"),
    "bucket_3": ("backout_plan", "risk_impact_analysis"),
}

_RAW_PATH_RE = re.compile(
    r"\[?\b(?:raw|canonical|evidence)\.[A-Za-z0-9_.-]+(?:\[[0-9]+\])*\]?",
    re.IGNORECASE,
)
_INTERNAL_TOKEN_RE = re.compile(r"\bsource_ref(?:_map)?\b", re.IGNORECASE)
_MARKDOWN_FENCE_RE = re.compile(r"```[A-Za-z0-9_-]*|```")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")
_MULTIBLANK_RE = re.compile(r"\n{3,}")
_EMPTY_BRACKET_RE = re.compile(r"\[\s*\]")


def clean_servicenow_field_text(value: str) -> str:
    """Clean one ServiceNow field without changing business meaning."""

    text = remove_markdown_artifacts(value)
    text = remove_raw_reference_tokens(text)
    text = _remove_field_label(text)
    text = normalize_servicenow_whitespace(text)
    return text


def remove_raw_reference_tokens(value: str) -> str:
    """Remove raw/internal reference tokens from field text."""

    text = _RAW_PATH_RE.sub(" ", value)
    text = _INTERNAL_TOKEN_RE.sub(" ", text)
    text = _EMPTY_BRACKET_RE.sub(" ", text)
    text = re.sub(r"\(\s*\)", " ", text)
    return text


def normalize_servicenow_whitespace(value: str) -> str:
    """Normalize whitespace while preserving meaningful numbered lists."""

    lines = [_MULTISPACE_RE.sub(" ", line).strip() for line in value.splitlines()]
    text = "\n".join(line for line in lines)
    text = _MULTIBLANK_RE.sub("\n\n", text)
    text = re.sub(r"[ \t]+([.,;:])", r"\1", text)
    text = re.sub(r"\s+\]", "]", text)
    text = re.sub(r"\[\s+", "[", text)
    return text.strip()


def remove_markdown_artifacts(value: str) -> str:
    """Remove markdown code fences from generated text."""

    return _MARKDOWN_FENCE_RE.sub("", value)


def format_service_now_payload(payload: ServiceNowPayload | dict[str, Any]) -> ServiceNowPayload:
    """Return a clean ServiceNow payload with exactly the eight supported fields."""

    raw_payload = payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
    cleaned = {
        field: clean_servicenow_field_text(str(raw_payload.get(field, "")))
        for field in SERVICE_NOW_FIELD_NAMES
    }
    return ServiceNowPayload.model_validate(cleaned)


def build_traceability_report(
    build_id: int,
    llm_outputs: dict[str, Any],
    evidence_bundle: dict[str, Any],
    source_llm_outputs_path: str | None = None,
    source_evidence_bundle_path: str | None = None,
) -> TraceabilityReport:
    """Build field-level traceability from LLM evidence refs and evidence source maps."""

    source_ref_map = _safe_dict(evidence_bundle.get("source_ref_map"))
    field_traceability: dict[str, FieldTraceability] = {}
    warnings: list[str] = []
    if not source_ref_map:
        warnings.append("source_ref_map_missing")

    for bucket_name, field_names in BUCKET_FIELD_MAP.items():
        bucket = _safe_dict(llm_outputs.get(bucket_name))
        evidence_used = _string_list(bucket.get("evidence_used"))
        friendly_refs = [ref for ref in evidence_used if ref in source_ref_map]
        original_refs = [
            str(entry["original_ref"])
            for ref in friendly_refs
            if isinstance((entry := source_ref_map.get(ref)), dict)
            and entry.get("original_ref")
        ]
        notes: list[str] = []
        if evidence_used and not friendly_refs:
            notes.append("evidence_used did not match source_ref_map entries")
        if not evidence_used:
            notes.append("no evidence_used references supplied")
        for field_name in field_names:
            field_traceability[field_name] = FieldTraceability(
                field_name=field_name,
                evidence_used=evidence_used,
                friendly_refs=friendly_refs,
                original_refs=original_refs,
                notes=notes,
            )

    return TraceabilityReport(
        build_id=build_id,
        generated_at=datetime.now(UTC),
        source_llm_outputs_path=source_llm_outputs_path,
        source_evidence_bundle_path=source_evidence_bundle_path,
        field_traceability=field_traceability,
        source_ref_map=source_ref_map,
        warnings=warnings,
    )


def _remove_field_label(value: str) -> str:
    text = value
    labels = {
        "change_description": "change description",
        "short_change_description": "short change description",
        "justification": "justification",
        "testing_performed": "testing performed",
        "implementation_plan": "implementation plan",
        "validation_plan": "validation plan",
        "backout_plan": "backout plan",
        "risk_impact_analysis": "risk impact analysis",
    }
    for snake_label, human_label in labels.items():
        pattern = re.compile(
            rf"^\s*(?:{re.escape(snake_label)}|{re.escape(human_label)})\s*:\s*",
            re.IGNORECASE,
        )
        text = pattern.sub("", text)
    return text


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item.strip()]
