"""Safe JSON inspection and size guards for LangGraph checkpoint state."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

DEFAULT_GRAPH_STATE_WARN_BYTES = 262_144
DEFAULT_GRAPH_STATE_MAX_BYTES = 1_048_576
DEFAULT_DIAGNOSTIC_MAX_DEPTH = 12
DEFAULT_DIAGNOSTIC_MAX_ITEMS = 1_000
DEFAULT_LARGEST_KEY_COUNT = 5


class GraphStateValidationError(ValueError):
    """Base error for an unsafe graph-state payload."""

    code = "GRAPH_STATE_NOT_JSON_SERIALIZABLE"

    def __init__(self, message: str, diagnostics: dict[str, Any]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class GraphStateTooLargeError(GraphStateValidationError):
    """Raised before a state update exceeds the application hard limit."""

    code = "GRAPH_STATE_TOO_LARGE"


class GraphStateUnsupportedTypeError(GraphStateValidationError):
    """Raised when a graph state contains unsupported Python values."""

    code = "GRAPH_STATE_UNSUPPORTED_TYPE"


def to_json_safe(value: object, *, context: str = "state") -> Any:
    """Convert explicitly supported Python values to JSON-compatible equivalents.

    Arbitrary custom objects, exception instances, clients, generators, and other
    runtime-only values are rejected instead of being converted with ``str()``.
    """

    return _to_json_safe(value, path=f"${context}", active_ids=set())


def json_safe_type_summary(value: object) -> dict[str, object]:
    """Return type, size, and serialization status without retaining values."""

    non_serializable_paths = find_non_json_serializable_paths(value)
    size_bytes = estimate_json_size_bytes(value)
    return {
        "python_type": _type_name(value),
        "estimated_size_bytes": size_bytes,
        "serialization_succeeds": size_bytes is not None and not non_serializable_paths,
        "non_serializable_paths": non_serializable_paths,
    }


def estimate_json_size_bytes(value: object) -> int | None:
    """Return compact UTF-8 JSON size, or ``None`` when strict serialization fails."""

    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError):
        return None
    return len(serialized.encode("utf-8"))


def find_non_json_serializable_paths(
    value: object,
    *,
    max_depth: int = DEFAULT_DIAGNOSTIC_MAX_DEPTH,
    max_items: int = DEFAULT_DIAGNOSTIC_MAX_ITEMS,
) -> list[str]:
    """Find bounded key paths and types that strict JSON cannot serialize."""

    findings: list[str] = []
    visited: set[int] = set()
    inspected = 0

    def inspect(item: object, path: str, depth: int) -> None:
        nonlocal inspected
        if inspected >= max_items:
            return
        inspected += 1
        if item is None or isinstance(item, str | int | bool):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                findings.append(f"{path} (float)")
            return
        if depth >= max_depth:
            return
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in visited:
                findings.append(f"{path} ({_type_name(item)}; cycle)")
                return
            visited.add(identity)
            for index, (key, child) in enumerate(item.items()):
                if index >= max_items or inspected >= max_items:
                    break
                if not isinstance(key, str):
                    findings.append(f"{path} ({_type_name(key)} dictionary key)")
                    child_path = f"{path}[key:{_type_name(key)}]"
                else:
                    child_path = _path_for_key(path, key)
                inspect(child, child_path, depth + 1)
            visited.remove(identity)
            return
        if isinstance(item, list):
            identity = id(item)
            if identity in visited:
                findings.append(f"{path} (list; cycle)")
                return
            visited.add(identity)
            for index, child in enumerate(item):
                if index >= max_items or inspected >= max_items:
                    break
                inspect(child, f"{path}[{index}]", depth + 1)
            visited.remove(identity)
            return
        findings.append(f"{path} ({_type_name(item)})")

    inspect(value, "$", 0)
    return findings


def assert_json_serializable(value: object, context: str) -> None:
    """Raise a safe error when a value is not strict JSON state."""

    paths = find_non_json_serializable_paths(value)
    size_bytes = estimate_json_size_bytes(value)
    if paths or size_bytes is None:
        diagnostics = {
            "context": context,
            "python_type": _type_name(value),
            "estimated_size_bytes": size_bytes,
            "non_serializable_paths": paths,
        }
        raise GraphStateUnsupportedTypeError(
            f"{context} contains values that are not JSON serializable.",
            diagnostics,
        )


def graph_state_diagnostics(
    state: Mapping[str, object],
    *,
    phase: str,
    largest_key_count: int = DEFAULT_LARGEST_KEY_COUNT,
) -> dict[str, Any]:
    """Build bounded state diagnostics containing no graph-state values."""

    state_dict = dict(state)
    total_size = estimate_json_size_bytes(state_dict)
    non_serializable = find_non_json_serializable_paths(state_dict)
    key_summaries: list[dict[str, Any]] = []
    for key, value in state_dict.items():
        key_summaries.append(
            {
                "key": str(key),
                "size_bytes": estimate_json_size_bytes(value),
                "type": _type_name(value),
            }
        )
    key_summaries.sort(
        key=lambda item: item["size_bytes"] if isinstance(item["size_bytes"], int) else -1,
        reverse=True,
    )
    return {
        "phase": phase,
        "state_keys": sorted(str(key) for key in state_dict),
        "state_size_bytes": total_size,
        "largest_keys": key_summaries[: max(0, largest_key_count)],
        "non_serializable_paths": non_serializable,
        "serialization_succeeds": total_size is not None and not non_serializable,
    }


def validate_graph_state(
    state: Mapping[str, object],
    *,
    context: str,
    warn_bytes: int = DEFAULT_GRAPH_STATE_WARN_BYTES,
    max_bytes: int = DEFAULT_GRAPH_STATE_MAX_BYTES,
) -> dict[str, Any]:
    """Validate state JSON shape and application-level checkpoint size limits."""

    resolved_warn, resolved_max = _resolved_limits(warn_bytes, max_bytes)
    diagnostics = graph_state_diagnostics(state, phase=context)
    diagnostics["warn_bytes"] = resolved_warn
    diagnostics["max_bytes"] = resolved_max
    paths = diagnostics["non_serializable_paths"]
    size_bytes = diagnostics["state_size_bytes"]
    if paths or size_bytes is None:
        raise GraphStateUnsupportedTypeError(
            f"{context} is not JSON serializable.",
            diagnostics,
        )
    if size_bytes > resolved_max:
        raise GraphStateTooLargeError(
            f"{context} exceeds the configured graph-state hard limit.",
            diagnostics,
        )
    diagnostics["warning_required"] = size_bytes > resolved_warn
    return diagnostics


def classify_platform_persistence_failure(
    exc: BaseException,
    diagnostics: Mapping[str, object],
) -> dict[str, object]:
    """Classify persistence errors without exposing exception messages or internals."""

    paths = diagnostics.get("non_serializable_paths")
    size_bytes = diagnostics.get("state_size_bytes")
    max_bytes = diagnostics.get("max_bytes", DEFAULT_GRAPH_STATE_MAX_BYTES)
    if isinstance(paths, list) and paths:
        classification = "likely_serialization_state_shape_failure"
        retryable = False
    elif isinstance(size_bytes, int) and isinstance(max_bytes, int) and size_bytes > max_bytes:
        classification = "likely_oversized_state_failure"
        retryable = False
    else:
        exception_name = type(exc).__name__.lower()
        message = str(exc).lower()
        is_platform_database = any(
            token in exception_name or token in message
            for token in ("pgcosmos", "postgres", "checkpoint", "database query")
        )
        is_transient = any(
            token in message
            for token in (
                "timeout",
                "timed out",
                "temporar",
                "connection reset",
                "connection refused",
                "deadlock",
                "too many connections",
                "rate limit",
                "unavailable",
            )
        )
        if is_platform_database and is_transient:
            classification = "likely_transient_platform_persistence_failure"
        elif is_platform_database:
            classification = "unknown_platform_persistence_failure"
        else:
            classification = "application_operation_failure"
        retryable = is_platform_database
    return {
        "failure_classification": classification,
        "retryable": retryable,
        "retry_owner": "enterprise_langgraph_platform" if retryable else None,
    }


def exception_type_chain(exc: BaseException, *, max_depth: int = 8) -> list[str]:
    """Return bounded exception/cause type names without exception messages."""

    chain: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and len(chain) < max_depth and id(current) not in seen:
        seen.add(id(current))
        chain.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    return chain


def _to_json_safe(value: object, *, path: str, active_ids: set[int]) -> Any:
    if value is None or isinstance(value, str | int | bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise GraphStateUnsupportedTypeError(
                f"{path} contains a non-finite float.",
                {"context": path, "python_type": "float"},
            )
        return value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, UUID | Path):
        return str(value)
    if isinstance(value, Enum):
        return _to_json_safe(value.value, path=path, active_ids=active_ids)
    if isinstance(value, BaseException):
        raise GraphStateUnsupportedTypeError(
            f"{path} contains an exception instance.",
            {"context": path, "python_type": _type_name(value)},
        )
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")  # type: ignore[attr-defined]
        return _to_json_safe(dumped, path=path, active_ids=active_ids)
    if is_dataclass(value) and not isinstance(value, type):
        return _to_json_safe(asdict(value), path=path, active_ids=active_ids)
    if isinstance(value, Mapping):
        identity = id(value)
        _assert_not_cycle(identity, path, value, active_ids)
        active_ids.add(identity)
        try:
            converted: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str):
                    raise GraphStateUnsupportedTypeError(
                        f"{path} contains a non-string dictionary key.",
                        {"context": path, "python_type": _type_name(key)},
                    )
                converted[key] = _to_json_safe(
                    item,
                    path=_path_for_key(path, key),
                    active_ids=active_ids,
                )
            return converted
        finally:
            active_ids.remove(identity)
    if isinstance(value, list | tuple | set | frozenset):
        identity = id(value)
        _assert_not_cycle(identity, path, value, active_ids)
        active_ids.add(identity)
        try:
            return [
                _to_json_safe(item, path=f"{path}[{index}]", active_ids=active_ids)
                for index, item in enumerate(value)
            ]
        finally:
            active_ids.remove(identity)
    raise GraphStateUnsupportedTypeError(
        f"{path} contains an unsupported Python value.",
        {"context": path, "python_type": _type_name(value)},
    )


def _assert_not_cycle(
    identity: int,
    path: str,
    value: object,
    active_ids: set[int],
) -> None:
    if identity in active_ids:
        raise GraphStateUnsupportedTypeError(
            f"{path} contains a cyclic reference.",
            {"context": path, "python_type": _type_name(value)},
        )


def _resolved_limits(warn_bytes: int, max_bytes: int) -> tuple[int, int]:
    resolved_warn = max(1, int(warn_bytes))
    resolved_max = max(1, int(max_bytes))
    if resolved_warn > resolved_max:
        resolved_warn = resolved_max
    return resolved_warn, resolved_max


def _path_for_key(parent: str, key: str) -> str:
    if key.isidentifier():
        return f"{parent}.{key}"
    return f"{parent}[{json.dumps(key, ensure_ascii=True)}]"


def _type_name(value: object) -> str:
    value_type = type(value)
    module = value_type.__module__
    return value_type.__name__ if module == "builtins" else f"{module}.{value_type.__name__}"
