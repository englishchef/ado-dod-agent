"""Tests for Phase 8 API models."""

from __future__ import annotations

from backend.app.models.api import GenerateRunRequest, GenerateRunResponse
from pydantic import ValidationError
from pytest import raises


def test_generate_run_request_validates_valid_request() -> None:
    request = GenerateRunRequest(
        organization="org",
        project="proj",
        build_id=123,
        mode="pipeline",
    )

    assert request.organization == "org"
    assert request.mode == "pipeline"


def test_generate_run_request_rejects_missing_organization() -> None:
    with raises(ValidationError):
        GenerateRunRequest(organization="", project="proj", build_id=123)


def test_generate_run_request_rejects_missing_project() -> None:
    with raises(ValidationError):
        GenerateRunRequest(organization="org", project="", build_id=123)


def test_generate_run_request_rejects_non_positive_build_id() -> None:
    with raises(ValidationError):
        GenerateRunRequest(organization="org", project="proj", build_id=0)


def test_generate_run_response_serializes() -> None:
    response = GenerateRunResponse(
        run_id="dod-run-1",
        correlation_id="corr-1",
        status="completed",
        build_id=123,
        organization="org",
        project="proj",
        service_now_payload={"change_description": "Change"},
        confidence={"overall": 0.8},
        artifact_paths={"run_summary": "summary.json"},
        warnings=[],
        errors=[],
    )

    payload = response.model_dump(mode="json")

    assert payload["run_id"] == "dod-run-1"
    assert payload["confidence"]["overall"] == 0.8
