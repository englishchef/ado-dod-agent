"""Focused tests for checkpoint-safe graph-state serialization."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from backend.app.utils.state_serialization import (
    GraphStateTooLargeError,
    GraphStateUnsupportedTypeError,
    classify_platform_persistence_failure,
    estimate_json_size_bytes,
    exception_type_chain,
    find_non_json_serializable_paths,
    json_safe_type_summary,
    to_json_safe,
    validate_graph_state,
)
from pydantic import BaseModel


class _Model(BaseModel):
    created_at: datetime


class _CustomClient:
    pass


def test_plain_compact_state_serializes_successfully() -> None:
    state = {"run_id": "run-1", "build_id": 7, "artifact_paths": {}, "warnings": []}

    diagnostics = validate_graph_state(state, context="test")

    assert diagnostics["serialization_succeeds"] is True
    assert diagnostics["state_size_bytes"] == estimate_json_size_bytes(state)


def test_supported_runtime_values_are_normalized() -> None:
    value = {
        "when": datetime(2026, 7, 17, 12, 30, tzinfo=UTC),
        "id": UUID("12345678-1234-5678-1234-567812345678"),
        "model": _Model(created_at=datetime(2026, 7, 17, tzinfo=UTC)),
        "items": ("a", "b"),
    }

    normalized = to_json_safe(value)

    assert normalized["when"] == "2026-07-17T12:30:00+00:00"
    assert normalized["id"] == "12345678-1234-5678-1234-567812345678"
    assert normalized["model"]["created_at"].startswith("2026-07-17")
    assert normalized["items"] == ["a", "b"]


def test_exception_and_custom_client_are_rejected() -> None:
    with pytest.raises(GraphStateUnsupportedTypeError, match="exception instance"):
        to_json_safe(RuntimeError("do not expose this"))
    with pytest.raises(GraphStateUnsupportedTypeError, match="unsupported Python value"):
        to_json_safe(_CustomClient())


def test_cyclic_object_is_reported_without_infinite_traversal() -> None:
    cyclic: list[object] = []
    cyclic.append(cyclic)

    findings = find_non_json_serializable_paths(cyclic)

    assert findings == ["$[0] (list; cycle)"]
    assert estimate_json_size_bytes(cyclic) is None


def test_diagnostics_never_include_secret_like_values() -> None:
    secret = "super-secret-access-token-value"
    summary = json_safe_type_summary({"access_token": _CustomClient(), "value": secret})
    rendered = repr(summary)

    assert "$.access_token" in rendered
    assert secret not in rendered


def test_state_warning_and_hard_limits_use_key_size_summaries_only() -> None:
    state = {"run_id": "run-1", "payload": "sensitive-value-" * 20}

    warning = validate_graph_state(state, context="test", warn_bytes=50, max_bytes=1_000)
    assert warning["warning_required"] is True
    assert warning["largest_keys"][0]["key"] == "payload"
    assert "sensitive-value" not in repr(warning)

    with pytest.raises(GraphStateTooLargeError) as raised:
        validate_graph_state(state, context="test", warn_bytes=10, max_bytes=100)
    assert raised.value.code == "GRAPH_STATE_TOO_LARGE"
    assert "sensitive-value" not in repr(raised.value.diagnostics)


def test_platform_persistence_classification_separates_state_and_transient_failures() -> None:
    class PGCosmosError(RuntimeError):
        pass

    safe = validate_graph_state({"run_id": "run-1"}, context="test")
    unknown = classify_platform_persistence_failure(
        PGCosmosError("Database query failed"),
        safe,
    )
    transient = classify_platform_persistence_failure(
        PGCosmosError("temporary connection timeout"),
        safe,
    )

    assert unknown["failure_classification"] == "unknown_platform_persistence_failure"
    assert unknown["retryable"] is True
    assert transient["failure_classification"] == (
        "likely_transient_platform_persistence_failure"
    )
    assert transient["retry_owner"] == "enterprise_langgraph_platform"


def test_exception_type_chain_omits_exception_messages() -> None:
    secret = "secret-token-value"
    cause = ValueError(secret)
    outer = RuntimeError(secret)
    outer.__cause__ = cause

    chain = exception_type_chain(outer)

    assert chain == ["RuntimeError", "ValueError"]
    assert secret not in repr(chain)
