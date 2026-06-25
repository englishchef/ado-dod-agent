"""Safe redaction and trace-summary helpers for DoD observability."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"
MAX_STRING_LENGTH = 500

SECRET_KEY_PATTERNS = {
    "authorization",
    "bearer",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "api_key",
    "key",
    "secret",
    "password",
    "credential",
    "connection_string",
    "cosmos_key",
    "azure_client_secret",
    "langsmith_api_key",
    "openai_api_key",
    "ado_pat",
    "system_accesstoken",
}

RAW_CONTENT_KEY_PATTERNS = {
    "env",
    "environment",
    "environment_variables",
    "raw_payload",
    "raw_ado_payload",
    "ado_payload",
    "work_item_description",
    "description_html",
    "pr_comments",
    "pull_request_comments",
    "prompt",
    "prompts",
    "messages",
    "llm_messages",
    "evidence_bundle",
    "evidence_bundle_content",
    "service_now_payload",
    "servicenow_payload",
}

TRACE_METADATA_ALLOWLIST = {
    "run_id",
    "build_id",
    "organization",
    "project",
    "correlation_id",
    "graph_name",
    "assistant_name",
    "storage_backend",
    "status",
    "rule_recommended_status",
    "highest_rule_severity",
    "final_confidence",
    "test_completeness_score",
    "artifact_count",
    "duration_ms",
    "phase_durations_ms",
    "error_code",
    "error_category",
    "pipeline_id",
    "pipeline_name",
    "build_number",
    "branch",
    "requested_by",
    "source",
    "mode",
    "trace_mode",
    "summary",
    "debug",
}


def redact_value(value: Any) -> Any:
    """Redact nested values without retaining partial secret-like strings."""

    if isinstance(value, Mapping):
        return redact_dict(dict(value))
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return _truncate_string(value)
    return value


def redact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted copy of a dictionary."""

    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_key = _normalize_key(key)
        if _is_secret_key(normalized_key) or _is_raw_content_key(normalized_key):
            redacted[str(key)] = REDACTED
        else:
            redacted[str(key)] = redact_value(value)
    return redacted


def safe_trace_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    """Return compact, allowlisted metadata safe for LangSmith traces."""

    safe: dict[str, Any] = {}
    for key, value in payload.items():
        key_text = str(key)
        normalized_key = _normalize_key(key_text)
        if normalized_key not in TRACE_METADATA_ALLOWLIST:
            if _is_secret_key(normalized_key) or _is_raw_content_key(normalized_key):
                continue
            if isinstance(value, dict | list | tuple):
                continue
        safe[key_text] = redact_value(value)
    return safe


def safe_run_summary_for_trace(result: dict[str, Any]) -> dict[str, Any]:
    """Build a safe DoD run summary for trace metadata or debug-redacted output."""

    confidence = result.get("confidence")
    rule_evaluation = result.get("rule_evaluation")
    artifact_paths = result.get("artifact_paths")
    errors = result.get("errors")
    summary = rule_evaluation.get("summary") if isinstance(rule_evaluation, dict) else {}

    payload = {
        "run_id": result.get("run_id"),
        "build_id": result.get("build_id"),
        "organization": result.get("organization"),
        "project": result.get("project"),
        "status": result.get("status"),
        "mode": result.get("mode"),
        "source": result.get("source"),
        "storage_backend": result.get("storage_backend"),
        "duration_ms": result.get("duration_ms"),
        "phase_durations_ms": result.get("phase_durations_ms"),
        "artifact_count": len(artifact_paths) if isinstance(artifact_paths, dict) else None,
        "final_confidence": _overall_confidence(confidence),
        "rule_recommended_status": (
            summary.get("recommended_status") if isinstance(summary, dict) else None
        ),
        "highest_rule_severity": (
            summary.get("highest_severity") if isinstance(summary, dict) else None
        ),
        "test_completeness_score": (
            rule_evaluation.get("test_completeness_score")
            if isinstance(rule_evaluation, dict)
            else None
        ),
        "error_code": _first_error_value(errors, "code"),
        "error_category": _first_error_value(errors, "phase"),
    }
    return safe_trace_metadata({key: value for key, value in payload.items() if value is not None})


def _normalize_key(key: Any) -> str:
    return str(key).strip().lower()


def _is_secret_key(normalized_key: str) -> bool:
    return any(pattern in normalized_key for pattern in SECRET_KEY_PATTERNS)


def _is_raw_content_key(normalized_key: str) -> bool:
    return any(pattern in normalized_key for pattern in RAW_CONTENT_KEY_PATTERNS)


def _truncate_string(value: str) -> str:
    if len(value) <= MAX_STRING_LENGTH:
        return value
    return value[:MAX_STRING_LENGTH] + "...[TRUNCATED]"


def _overall_confidence(confidence: Any) -> Any:
    if isinstance(confidence, dict):
        return confidence.get("overall")
    return None


def _first_error_value(errors: Any, key: str) -> Any:
    if not isinstance(errors, list) or not errors:
        return None
    first = errors[0]
    if not isinstance(first, dict):
        return None
    return first.get(key)
