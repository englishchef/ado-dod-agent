"""Friendly evidence source reference normalization."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from backend.app.models.evidence import EvidenceSourceRef

_UNSUPPORTED_REF_CHARS_RE = re.compile(r"[^A-Za-z0-9_.-]+")
_WHITESPACE_RE = re.compile(r"\s+")
_SOURCE_TYPE_ALIASES = {
    "workitem": "work_item",
    "work_items": "work_item",
    "pullrequest": "pull_request",
    "pull_requests": "pull_request",
    "pipeline_stage": "stage",
    "pipeline_job": "job",
    "pipeline_task": "task",
    "timeline_task": "task",
    "test_runs": "test_run",
    "test_results": "test_result",
}


def _get_value(item: dict[str, Any] | Any, key: str) -> Any:
    if isinstance(item, dict):
        return item.get(key)
    return getattr(item, key, None)


def _first_value(item: dict[str, Any] | Any, keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = _get_value(item, key)
        if value is not None and str(value).strip():
            return value
    return None


def safe_ref_name(value: str) -> str:
    """Return a readable value safe for use after an evidence ref prefix."""

    normalized = _WHITESPACE_RE.sub("_", value.strip())
    normalized = _UNSUPPORTED_REF_CHARS_RE.sub("_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_.-")
    return normalized or "unknown"


def _stable_unknown_ref(item: dict[str, Any] | Any, original_ref: str | None) -> str:
    seed = original_ref
    if seed is None:
        if isinstance(item, dict):
            seed = repr(sorted(item.items()))
        else:
            seed = repr(item)
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return f"evidence:{digest}"


def _source_type_key(source_type: str) -> str:
    key = safe_ref_name(source_type.lower().strip().replace(" ", "_"))
    return _SOURCE_TYPE_ALIASES.get(key, key)


def _safe_first_ref_value(item: dict[str, Any] | Any, keys: tuple[str, ...]) -> str:
    return safe_ref_name(str(_first_value(item, keys) or "unknown"))


def _display_name(source_type: str, item: dict[str, Any] | Any) -> str | None:
    keys_by_source_type: dict[str, tuple[str, ...]] = {
        "work_item": ("title", "id"),
        "commit": ("message", "id"),
        "pull_request": ("title", "id"),
        "stage": ("name", "id"),
        "job": ("name", "id"),
        "task": ("name", "id"),
        "artifact": ("name",),
        "test_run": ("name", "id"),
        "test_result": ("test_name", "id"),
    }
    value = _first_value(item, keys_by_source_type.get(source_type, ("name", "title", "id")))
    return str(value) if value is not None else None


def build_source_ref_map_entry(
    friendly_ref: str,
    source_type: str,
    original_ref: str | None = None,
    display_name: str | None = None,
) -> EvidenceSourceRef:
    """Build one source reference map entry."""

    return EvidenceSourceRef(
        friendly_ref=friendly_ref,
        original_ref=original_ref,
        source_type=source_type,
        display_name=display_name,
    )


def normalize_source_ref(
    source_type: str,
    item: dict[str, Any] | Any,
    original_ref: str | None = None,
) -> tuple[str, EvidenceSourceRef]:
    """Return a friendly source reference and traceability map entry."""

    source_key = _source_type_key(source_type)
    raw_ref = original_ref or _get_value(item, "source_ref")

    if source_key == "work_item":
        friendly_ref = f"work_item:{_first_value(item, ('id',))}"
    elif source_key == "commit":
        commit_id = str(_first_value(item, ("id", "commit_id")) or "").strip()
        short_sha = commit_id[:7] if commit_id else "unknown"
        friendly_ref = f"commit:{safe_ref_name(short_sha)}"
    elif source_key == "pull_request":
        friendly_ref = f"pull_request:{_first_value(item, ('id', 'pull_request_id'))}"
    elif source_key == "stage":
        friendly_ref = f"pipeline_stage:{_safe_first_ref_value(item, ('name', 'id'))}"
    elif source_key == "job":
        friendly_ref = f"pipeline_job:{_safe_first_ref_value(item, ('name', 'id'))}"
    elif source_key == "task":
        friendly_ref = f"pipeline_task:{_safe_first_ref_value(item, ('name', 'id'))}"
    elif source_key == "artifact":
        friendly_ref = f"artifact:{_safe_first_ref_value(item, ('name',))}"
    elif source_key == "test_run":
        friendly_ref = f"test_run:{_safe_first_ref_value(item, ('name', 'id'))}"
    elif source_key == "test_result":
        friendly_ref = f"test_result:{_safe_first_ref_value(item, ('test_name', 'id'))}"
    else:
        friendly_ref = _stable_unknown_ref(item, raw_ref)

    entry = build_source_ref_map_entry(
        friendly_ref=friendly_ref,
        original_ref=str(raw_ref) if raw_ref is not None else None,
        source_type=source_key,
        display_name=_display_name(source_key, item),
    )
    return friendly_ref, entry
