"""Run orchestration API endpoints."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.app.models.api import (
    ApiIssue,
    ArtifactResponse,
    GenerateRunRequest,
    GenerateRunResponse,
)
from backend.app.models.canonical import CanonicalDodDocument
from backend.app.models.dod_contracts import (
    normalize_dod_run_input,
    serialize_dod_run_output,
)
from backend.app.models.inputs import (
    BuildEvidenceInput,
    CollectRawInput,
    GenerateRunInput,
    NormalizeRawInput,
)
from backend.app.models.outputs import (
    BuildEvidenceResponse,
    NormalizeRawResponse,
    RawCollectionResult,
)
from backend.app.models.run_summary import DodRunSummary, RunIssue
from backend.app.services.collectors.raw_metadata import collect_raw_metadata
from backend.app.services.evidence.builder import build_evidence_bundle, build_evidence_summary
from backend.app.services.normalizers.canonical import (
    build_canonical_summary,
    normalize_raw_bundle,
)
from backend.app.services.orchestration.dod_run_service import run_dod_agent
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.services.storage.storage_factory import get_storage_store
from backend.app.utils.config import get_settings
from backend.app.utils.constants import CORRELATION_ID_HEADER
from backend.app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/generate", response_model=GenerateRunResponse)
def generate_run(
    request: GenerateRunRequest,
    x_correlation_id: str | None = Header(default=None, alias=CORRELATION_ID_HEADER),
) -> GenerateRunResponse | JSONResponse:
    """Run the Phase 7 DoD agent and return the final ServiceNow-ready payload."""

    started_at = time.perf_counter()
    correlation_id = request.correlation_id or x_correlation_id or str(uuid4())
    contract_input = normalize_dod_run_input(
        {**request.model_dump(mode="json"), "correlation_id": correlation_id}
    )
    try:
        summary = run_dod_agent(contract_input.model_dump(mode="json"))
    except Exception:
        logger.warning(
            "dod_generate_failed correlation_id=%s build_id=%s organization=%s project=%s",
            correlation_id,
            request.build_id,
            request.organization,
            request.project,
        )
        return _safe_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="orchestration_failed",
            message="DoD agent orchestration failed.",
            correlation_id=correlation_id,
        )

    contract_output = serialize_dod_run_output(summary, fallback_input=contract_input)
    response = _response_from_contract(contract_output, contract_input)
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    overall = _overall_confidence(summary.confidence)
    logger.info(
        (
            "dod_generate_complete run_id=%s correlation_id=%s build_id=%s "
            "organization=%s project=%s status=%s warning_count=%s error_count=%s "
            "confidence_overall=%s duration_ms=%s"
        ),
        summary.run_id,
        correlation_id,
        summary.build_id,
        summary.organization,
        summary.project,
        summary.status,
        len(summary.warnings),
        len(summary.errors),
        overall,
        duration_ms,
    )
    if summary.status == "failed" and not summary.service_now_payload:
        return _safe_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="orchestration_failed",
            message="DoD agent orchestration failed before producing a usable payload.",
            correlation_id=correlation_id,
            details={"run_id": summary.run_id, "build_id": summary.build_id},
        )
    return response


@router.post("/orchestrate")
def orchestrate_run(request: GenerateRunInput) -> dict[str, Any]:
    """Run Phase 7A LangGraph orchestration without ServiceNow writeback."""

    summary = run_dod_agent(request.model_dump())
    return summary.model_dump(mode="json")


@router.get("/{build_id}/summary", response_model=ArtifactResponse)
def get_run_summary_artifact(build_id: int) -> ArtifactResponse:
    """Return persisted run summary without regenerating artifacts."""

    store = _storage_store()
    return _artifact_response(
        store=store,
        build_id=build_id,
        artifact_type="summary",
        filename="run_summary.json",
        load=store.load_run_summary,
    )


@router.get("/{build_id}/payload", response_model=ArtifactResponse)
def get_payload_artifact(build_id: int) -> ArtifactResponse:
    """Return persisted ServiceNow-ready payload without regenerating artifacts."""

    store = _storage_store()
    return _artifact_response(
        store=store,
        build_id=build_id,
        artifact_type="payload",
        filename="service_now_payload.json",
        load=store.load_service_now_payload,
    )


@router.get("/{build_id}/confidence", response_model=ArtifactResponse)
def get_confidence_artifact(build_id: int) -> ArtifactResponse:
    """Return persisted confidence artifact without regenerating artifacts."""

    store = _storage_store()
    return _artifact_response(
        store=store,
        build_id=build_id,
        artifact_type="confidence",
        filename="confidence.json",
        load=store.load_confidence,
    )


@router.get("/{build_id}/routing-decisions", response_model=ArtifactResponse)
def get_routing_decisions_artifact(build_id: int) -> ArtifactResponse:
    """Return persisted routing decisions without regenerating artifacts."""

    store = _storage_store()
    return _artifact_response(
        store=store,
        build_id=build_id,
        artifact_type="routing_decisions",
        filename="routing_decisions.json",
        load=store.load_routing_decisions,
    )


@router.get("/{build_id}/traceability-report", response_model=ArtifactResponse)
def get_traceability_report_artifact(build_id: int) -> ArtifactResponse:
    """Return persisted traceability report without regenerating artifacts."""

    store = _storage_store()
    return _artifact_response(
        store=store,
        build_id=build_id,
        artifact_type="traceability_report",
        filename="traceability_report.json",
        load=store.load_traceability_report,
    )


@router.get("/{build_id}/rule-evaluation", response_model=ArtifactResponse)
def get_rule_evaluation_artifact(build_id: int) -> ArtifactResponse:
    """Return persisted rule evaluation without regenerating artifacts."""

    store = _storage_store()
    return _artifact_response(
        store=store,
        build_id=build_id,
        artifact_type="rule_evaluation",
        filename="rule_evaluation.json",
        load=store.load_rule_evaluation,
    )


@router.post("/collect-raw", response_model=RawCollectionResult)
async def collect_raw(request: CollectRawInput) -> RawCollectionResult:
    """Collect raw build metadata and persist local artifacts."""

    result = await collect_raw_metadata(request)
    if result.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Raw metadata collection failed at mandatory build retrieval stage.",
                "collection_run_id": result.collection_run_id,
                "build_id": result.build_id,
                "errors": [error.model_dump() for error in result.errors],
            },
        )
    return result


@router.post("/normalize", response_model=NormalizeRawResponse)
async def normalize_raw(request: NormalizeRawInput) -> NormalizeRawResponse:
    """Normalize previously collected raw metadata into canonical structure."""

    settings = get_settings()
    store = _storage_store(settings)

    source_path: str | None = request.raw_bundle_path
    try:
        if request.raw_bundle_path:
            payload_text = Path(request.raw_bundle_path).read_text(encoding="utf-8")
            raw_bundle: dict[str, Any] = json.loads(payload_text)
        else:
            raw_bundle = store.load_raw_bundle(request.build_id)
            source_path = store.raw_path(request.build_id, "raw_bundle.json")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Raw bundle not found for build_id={request.build_id}.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Raw bundle is not valid JSON for build_id={request.build_id}.",
        ) from exc

    raw_bundle["build_id"] = request.build_id
    if request.organization:
        raw_bundle["organization"] = request.organization
    if request.project:
        raw_bundle["project"] = request.project

    document = normalize_raw_bundle(raw_bundle=raw_bundle, source_path=source_path)
    canonical_path = store.save_normalized_json(
        build_id=request.build_id,
        filename="canonical.json",
        payload=document.model_dump(mode="json"),
    )

    summary = build_canonical_summary(document, canonical_path)
    return NormalizeRawResponse.model_validate(summary)


@router.post("/build-evidence", response_model=BuildEvidenceResponse)
async def build_evidence(request: BuildEvidenceInput) -> BuildEvidenceResponse:
    """Build deterministic evidence buckets from canonical normalized metadata."""

    settings = get_settings()
    store = _storage_store(settings)

    source_path: str | None = request.canonical_path
    try:
        if request.canonical_path:
            payload_text = Path(request.canonical_path).read_text(encoding="utf-8")
            canonical_payload: dict[str, Any] = json.loads(payload_text)
        else:
            canonical_payload = store.load_canonical(request.build_id)
            source_path = store.normalized_path(request.build_id, "canonical.json")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canonical document not found for build_id={request.build_id}.",
        ) from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Canonical document is not valid JSON for build_id={request.build_id}.",
        ) from exc

    canonical_payload["build_id"] = request.build_id
    try:
        canonical_document = CanonicalDodDocument.model_validate(canonical_payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Canonical document has invalid schema for build_id={request.build_id}.",
        ) from exc
    evidence_bundle = build_evidence_bundle(
        canonical=canonical_document,
        source_path=source_path,
        max_items_per_section=request.max_items_per_section,
    )

    bucket_1_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="bucket_1_change_intent.json",
        payload=evidence_bundle.bucket_1.model_dump(mode="json"),
    )
    bucket_2_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="bucket_2_execution_validation.json",
        payload=evidence_bundle.bucket_2.model_dump(mode="json"),
    )
    bucket_3_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="bucket_3_rollback_risk.json",
        payload=evidence_bundle.bucket_3.model_dump(mode="json"),
    )
    bundle_path = store.save_evidence_json(
        build_id=request.build_id,
        filename="evidence_bundle.json",
        payload=evidence_bundle.model_dump(mode="json"),
    )
    summary = build_evidence_summary(
        bundle=evidence_bundle,
        bucket_paths={
            "bucket_1_change_intent_path": bucket_1_path,
            "bucket_2_execution_validation_path": bucket_2_path,
            "bucket_3_rollback_risk_path": bucket_3_path,
            "evidence_bundle_path": bundle_path,
        },
    )
    return BuildEvidenceResponse.model_validate(summary)


def _response_from_summary(
    summary: DodRunSummary,
    correlation_id: str | None,
) -> GenerateRunResponse:
    return GenerateRunResponse(
        run_id=summary.run_id,
        correlation_id=correlation_id,
        status=summary.status,
        build_id=summary.build_id,
        organization=summary.organization,
        project=summary.project,
        service_now_payload=summary.service_now_payload,
        confidence=summary.confidence,
        artifact_paths=summary.artifact_paths,
        warnings=[_api_issue_from_run_issue(issue) for issue in summary.warnings],
        errors=[_api_issue_from_run_issue(issue) for issue in summary.errors],
    )


def _response_from_contract(
    output: Any,
    input_data: Any,
) -> GenerateRunResponse:
    return GenerateRunResponse(
        run_id=output.run_id or "",
        correlation_id=input_data.correlation_id,
        status=output.status,
        build_id=output.build_id,
        organization=input_data.organization,
        project=input_data.project,
        service_now_payload=output.service_now_payload or None,
        confidence=output.confidence or None,
        artifact_paths=output.artifact_paths,
        warnings=[ApiIssue.model_validate(issue) for issue in output.warnings],
        errors=[ApiIssue.model_validate(issue) for issue in output.errors],
    )


def _api_issue_from_run_issue(issue: RunIssue) -> ApiIssue:
    return ApiIssue(
        severity=issue.severity,
        code=issue.code,
        message=issue.message,
        phase=issue.phase,
    )


def _artifact_response(
    *,
    store: LocalJsonStore,
    build_id: int,
    artifact_type: str,
    filename: str,
    load: Any,
) -> ArtifactResponse:
    try:
        content = load(build_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "failed",
                "message": f"{artifact_type} artifact not found for build_id={build_id}.",
                "code": "artifact_not_found",
                "details": {"build_id": build_id, "artifact_type": artifact_type},
            },
        ) from exc
    return ArtifactResponse(
        build_id=build_id,
        artifact_type=artifact_type,
        path=store.output_path(build_id, filename),
        content=content,
    )


def _safe_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    correlation_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "failed",
            "message": message,
            "code": code,
            "correlation_id": correlation_id,
            "details": details or {},
        },
    )


def _overall_confidence(confidence: dict[str, Any] | None) -> float | None:
    if not isinstance(confidence, dict):
        return None
    value = confidence.get("overall")
    if isinstance(value, int | float):
        return float(value)
    return None


def _storage_store(settings: Any | None = None) -> Any:
    resolved = settings or get_settings()
    if resolved.DOD_STORAGE_BACKEND == "local_json":
        return LocalJsonStore(resolved)
    return get_storage_store(resolved)
