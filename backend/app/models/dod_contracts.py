"""Shared external contract models for DoD agent runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DoDRunMode = Literal["pipeline", "local", "replay", "api"]


class DoDRunWarning(BaseModel):
    """API-safe warning emitted by a DoD run."""

    severity: str = "warning"
    code: str = ""
    message: str = ""
    phase: str | None = None


class DoDRunError(BaseModel):
    """API-safe error emitted by a DoD run."""

    severity: str = "error"
    code: str = ""
    message: str = ""
    phase: str | None = None


class DoDRunArtifactPaths(BaseModel):
    """Known artifact path fields with extension room for future artifacts."""

    model_config = ConfigDict(extra="allow")

    raw_bundle: str | None = None
    canonical: str | None = None
    evidence_bundle: str | None = None
    llm_outputs: str | None = None
    validated_output: str | None = None
    service_now_payload: str | None = None
    confidence: str | None = None
    traceability_report: str | None = None
    rule_evaluation: str | None = None
    routing_decisions: str | None = None
    run_summary: str | None = None


class DoDRuleEvaluationSummary(BaseModel):
    """Small rule summary safe to return from external run interfaces."""

    model_config = ConfigDict(extra="allow")

    highest_severity: str | None = None
    recommended_status: str | None = None
    triggered_rule_count: int | None = None
    warning_count: int | None = None
    review_count: int | None = None
    error_count: int | None = None
    test_completeness_score: dict[str, Any] | None = None


class DoDRunInput(BaseModel):
    """Structured input contract for FastAPI, CLI, and LangGraph invocation."""

    organization: str = Field(min_length=1)
    project: str = Field(min_length=1)
    build_id: int = Field(gt=0)
    mode: DoDRunMode = "pipeline"
    correlation_id: str | None = None
    requested_by: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("organization", "project")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must be a non-empty string.")
        return stripped


class DoDRunOutput(BaseModel):
    """Structured output contract for DoD agent run summaries."""

    run_id: str | None = None
    build_id: int
    status: str
    service_now_payload: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    rule_evaluation_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] | None = None


def normalize_dod_run_input(payload: Mapping[str, Any] | DoDRunInput) -> DoDRunInput:
    """Validate and normalize structured DoD run input."""

    if isinstance(payload, DoDRunInput):
        return payload
    return DoDRunInput.model_validate(dict(payload))


def serialize_dod_run_output(
    result: Any,
    fallback_input: DoDRunInput | None = None,
) -> DoDRunOutput:
    """Convert an orchestration result into the external DoD run output contract."""

    result_dict = _to_result_dict(result)
    rule_evaluation = result_dict.get("rule_evaluation")
    rule_evaluation_summary = result_dict.get("rule_evaluation_summary")
    if not isinstance(rule_evaluation_summary, dict):
        rule_evaluation_summary = _derive_rule_evaluation_summary(rule_evaluation)

    build_id = _int_or_default(
        result_dict.get("build_id"),
        fallback_input.build_id if fallback_input is not None else 0,
    )
    if build_id <= 0:
        raise ValueError("build_id is required to serialize DoD run output.")

    return DoDRunOutput(
        run_id=_optional_str(result_dict.get("run_id")),
        build_id=build_id,
        status=str(result_dict.get("status") or "error"),
        service_now_payload=_dict_or_empty(result_dict.get("service_now_payload")),
        confidence=_dict_or_empty(result_dict.get("confidence")),
        rule_evaluation_summary=rule_evaluation_summary,
        artifact_paths=_string_dict(result_dict.get("artifact_paths")),
        warnings=_list_of_dicts(result_dict.get("warnings")),
        errors=_list_of_dicts(result_dict.get("errors")),
        result=_safe_result_dict(result_dict),
    )


def _to_result_dict(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return dict(result)
    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="json")
        return dict(payload) if isinstance(payload, dict) else {}
    if is_dataclass(result) and not isinstance(result, type):
        payload = asdict(result)
        return dict(payload) if isinstance(payload, dict) else {}

    known_fields = (
        "run_id",
        "status",
        "build_id",
        "service_now_payload",
        "confidence",
        "rule_evaluation",
        "rule_evaluation_summary",
        "artifact_paths",
        "warnings",
        "errors",
    )
    return {field: getattr(result, field) for field in known_fields if hasattr(result, field)}


def _derive_rule_evaluation_summary(rule_evaluation: Any) -> dict[str, Any]:
    if not isinstance(rule_evaluation, dict):
        return {}

    summary = rule_evaluation.get("summary")
    if isinstance(summary, dict):
        derived = dict(summary)
    else:
        rules = rule_evaluation.get("rules_triggered")
        derived = _summarize_rules(rules if isinstance(rules, list) else [])

    score = rule_evaluation.get("test_completeness_score")
    if isinstance(score, dict):
        derived["test_completeness_score"] = dict(score)
    return derived


def _summarize_rules(rules: list[Any]) -> dict[str, Any]:
    severities = [_rule_severity(rule) for rule in rules]
    severity_order = {"info": 0, "warning": 1, "review": 2, "error": 3}
    highest = max(severities, key=lambda item: severity_order.get(item, -1), default=None)
    return {
        "highest_severity": highest,
        "recommended_status": _recommended_status(highest),
        "triggered_rule_count": len(rules),
        "warning_count": severities.count("warning"),
        "review_count": severities.count("review"),
        "error_count": severities.count("error"),
    }


def _rule_severity(rule: Any) -> str:
    if isinstance(rule, dict):
        return str(rule.get("severity") or "")
    return str(getattr(rule, "severity", "") or "")


def _recommended_status(highest: str | None) -> str:
    if highest == "error":
        return "failed"
    if highest == "review":
        return "needs_review"
    if highest == "warning":
        return "completed_with_warnings"
    return "completed"


def _safe_result_dict(result: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "run_id",
        "status",
        "build_id",
        "service_now_payload",
        "confidence",
        "rule_evaluation",
        "rule_evaluation_summary",
        "artifact_paths",
        "warnings",
        "errors",
        "schema_version",
        "organization",
        "project",
        "started_at",
        "completed_at",
    )
    return {key: result[key] for key in allowed if key in result}


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items() if item is not None}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            items.append(dict(item))
        elif hasattr(item, "model_dump"):
            payload = item.model_dump(mode="json")
            if isinstance(payload, dict):
                items.append(dict(payload))
        elif is_dataclass(item) and not isinstance(item, type):
            payload = asdict(item)
            if isinstance(payload, dict):
                items.append(dict(payload))
    return items


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
