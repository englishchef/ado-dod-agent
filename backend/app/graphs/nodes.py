"""Phase 7B LangGraph nodes that orchestrate existing services."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

from backend.app.graphs.state import (
    STATUS_COMPLETED,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_NEEDS_REVIEW,
    STATUS_STARTED,
    DodGraphState,
)
from backend.app.models.canonical import CanonicalDodDocument
from backend.app.models.inputs import CollectRawInput
from backend.app.models.routing import (
    EvidenceQualityAssessment,
    PromptStrategySelection,
    RiskTierAssessment,
    RoutingDecision,
    RoutingDecisionBundle,
)
from backend.app.models.run_summary import DodRunSummary, RunIssue
from backend.app.services.collectors.raw_metadata import collect_raw_metadata
from backend.app.services.evidence.builder import build_evidence_bundle
from backend.app.services.llm.generator import generate_all_buckets
from backend.app.services.normalizers.canonical import normalize_raw_bundle
from backend.app.services.routing.decision_recorder import make_decision
from backend.app.services.routing.evidence_quality import assess_evidence_quality
from backend.app.services.routing.prompt_strategy import select_prompt_strategy
from backend.app.services.routing.risk_tier import assess_risk_tier
from backend.app.services.rules.rule_engine import evaluate_rules
from backend.app.services.storage.local_store import LocalJsonStore
from backend.app.services.validation.service import validate_and_assemble_outputs
from backend.app.utils.config import get_settings


def validate_input_node(state: DodGraphState) -> DodGraphState:
    """Validate required input and initialize the run state."""

    now = _utc_now()
    input_data = dict(state.get("input") or {})
    build_id = _coerce_build_id(state.get("build_id", input_data.get("build_id")))
    organization = _coerce_str(state.get("organization", input_data.get("organization")))
    project = _coerce_str(state.get("project", input_data.get("project")))
    mode = _coerce_str(state.get("mode", input_data.get("mode"))) or "local"
    confidence_threshold = _coerce_float(input_data.get("confidence_threshold"))
    high_risk_confidence_threshold = _coerce_float(
        input_data.get("high_risk_confidence_threshold")
    )
    run_id = _coerce_str(state.get("run_id")) or f"dod-run-{_timestamp_for_id(now)}-{build_id or 0}"

    errors: list[dict[str, Any]] = []
    if build_id is None or build_id <= 0:
        errors.append(_issue("error", "invalid_build_id", "build_id is required.", "input"))
    if not organization:
        errors.append(_issue("error", "missing_organization", "organization is required.", "input"))
    if not project:
        errors.append(_issue("error", "missing_project", "project is required.", "input"))

    return {
        "run_id": run_id,
        "build_id": build_id or 0,
        "organization": organization or "",
        "project": project or "",
        "mode": mode,
        "confidence_threshold": confidence_threshold
        or float(get_settings().DOD_CONFIDENCE_THRESHOLD),
        "high_risk_confidence_threshold": high_risk_confidence_threshold
        or float(get_settings().DOD_HIGH_RISK_CONFIDENCE_THRESHOLD),
        "input": input_data,
        "status": STATUS_FAILED if errors else STATUS_STARTED,
        "started_at": _iso(now),
        "completed_at": state.get("completed_at"),
        "raw_result": state.get("raw_result"),
        "canonical_result": state.get("canonical_result"),
        "evidence_result": state.get("evidence_result"),
        "evidence_quality": state.get("evidence_quality"),
        "prompt_strategy": state.get("prompt_strategy"),
        "risk_tier": state.get("risk_tier"),
        "routing_decisions": list(state.get("routing_decisions") or []),
        "llm_outputs": state.get("llm_outputs"),
        "validated_output": state.get("validated_output"),
        "service_now_payload": state.get("service_now_payload"),
        "confidence": state.get("confidence"),
        "rule_evaluation": state.get("rule_evaluation"),
        "artifact_paths": dict(state.get("artifact_paths") or {}),
        "warnings": list(state.get("warnings") or []),
        "errors": [*list(state.get("errors") or []), *errors],
    }


def collect_raw_metadata_node(state: DodGraphState) -> DodGraphState:
    """Run the Phase 2 raw metadata collector."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        request = CollectRawInput(
            organization=state["organization"],
            project=state["project"],
            build_id=state["build_id"],
            mode=state.get("mode", "local"),
        )
        result = asyncio.run(collect_raw_metadata(request))
    except Exception as exc:
        return _with_error(state, "raw_collection_failed", str(exc), "collect_raw")

    payload = _model_dump(result)
    artifact_paths = _merge_artifact_paths(state, _extract_paths(payload.get("artifact_paths")))
    warnings = list(state.get("warnings") or [])
    errors = list(state.get("errors") or [])

    collector_errors = payload.get("errors")
    if isinstance(collector_errors, list):
        for item in collector_errors:
            issue = _collector_issue(item, phase="collect_raw")
            if payload.get("status") == "failed":
                errors.append(issue)
            else:
                warnings.append({**issue, "severity": "warning"})

    collector_statuses = payload.get("collector_statuses")
    if isinstance(collector_statuses, list):
        for item in collector_statuses:
            status = item.get("status") if isinstance(item, dict) else None
            if status in {"partial", "failed"}:
                name = item.get("name", "collector") if isinstance(item, dict) else "collector"
                warnings.append(
                    _issue(
                        "warning",
                        f"{name}_{status}",
                        f"Collector {name} finished with status {status}.",
                        "collect_raw",
                    )
                )

    status = (
        STATUS_FAILED
        if payload.get("status") == "failed"
        else state.get("status", STATUS_STARTED)
    )
    return {
        "raw_result": payload,
        "artifact_paths": artifact_paths,
        "warnings": warnings,
        "errors": errors,
        "status": status,
    }


def normalize_canonical_node(state: DodGraphState) -> DodGraphState:
    """Run Phase 3 canonical normalization from the raw bundle."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        store = LocalJsonStore(get_settings())
        raw_bundle_path = state.get("artifact_paths", {}).get(
            "raw_bundle",
            store.raw_path(state["build_id"], "raw_bundle.json"),
        )
        raw_bundle = store.load_raw_bundle(state["build_id"])
        raw_bundle["build_id"] = state["build_id"]
        raw_bundle["organization"] = state["organization"]
        raw_bundle["project"] = state["project"]
        document = normalize_raw_bundle(raw_bundle, source_path=raw_bundle_path)
        canonical_payload = document.model_dump(mode="json")
        canonical_path = store.save_normalized_json(
            state["build_id"],
            "canonical.json",
            canonical_payload,
        )
    except Exception as exc:
        return _with_error(state, "canonical_normalization_failed", str(exc), "normalize")

    warnings = [
        *list(state.get("warnings") or []),
        *_warnings_from_strings(
            _safe_list(canonical_payload.get("normalization_metadata", {}).get("warnings")),
            "normalize",
            "normalization_warning",
        ),
    ]
    return {
        "canonical_result": canonical_payload,
        "artifact_paths": _merge_artifact_paths(state, {"canonical": canonical_path}),
        "warnings": warnings,
    }


def build_evidence_buckets_node(state: DodGraphState) -> DodGraphState:
    """Run Phase 4 deterministic evidence bucket generation."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        store = LocalJsonStore(get_settings())
        canonical_path = state.get("artifact_paths", {}).get(
            "canonical",
            store.normalized_path(state["build_id"], "canonical.json"),
        )
        canonical_payload = state.get("canonical_result") or store.load_canonical(state["build_id"])
        canonical_document = CanonicalDodDocument.model_validate(canonical_payload)
        bundle = build_evidence_bundle(canonical_document, source_path=canonical_path)
        evidence_payload = bundle.model_dump(mode="json")
        bucket_1_path = store.save_evidence_json(
            state["build_id"],
            "bucket_1_change_intent.json",
            bundle.bucket_1.model_dump(mode="json"),
        )
        bucket_2_path = store.save_evidence_json(
            state["build_id"],
            "bucket_2_execution_validation.json",
            bundle.bucket_2.model_dump(mode="json"),
        )
        bucket_3_path = store.save_evidence_json(
            state["build_id"],
            "bucket_3_rollback_risk.json",
            bundle.bucket_3.model_dump(mode="json"),
        )
        evidence_bundle_path = store.save_evidence_json(
            state["build_id"],
            "evidence_bundle.json",
            evidence_payload,
        )
    except Exception as exc:
        return _with_error(state, "evidence_generation_failed", str(exc), "evidence")

    metadata = evidence_payload.get("generation_metadata", {})
    warnings = [
        *list(state.get("warnings") or []),
        *_warnings_from_strings(
            _safe_list(metadata.get("warnings")),
            "evidence",
            "evidence_warning",
        ),
        *_warnings_from_strings(
            _safe_list(metadata.get("missing_sections")),
            "evidence",
            "evidence_gap",
        ),
    ]
    return {
        "evidence_result": evidence_payload,
        "artifact_paths": _merge_artifact_paths(
            state,
            {
                "bucket_1_change_intent": bucket_1_path,
                "bucket_2_execution_validation": bucket_2_path,
                "bucket_3_rollback_risk": bucket_3_path,
                "evidence_bundle": evidence_bundle_path,
            },
        ),
        "warnings": warnings,
    }


def assess_evidence_quality_node(state: DodGraphState) -> DodGraphState:
    """Assess evidence quality for downstream routing."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        evidence_bundle = _load_evidence_bundle_from_state(state)
        assessment = assess_evidence_quality(evidence_bundle)
    except Exception as exc:
        return _with_error(state, "evidence_quality_assessment_failed", str(exc), "routing")

    decisions = list(state.get("routing_decisions") or [])
    decisions.extend(
        [
            _decision_json(
                make_decision(
                    "evidence_quality",
                    f"bucket_1_{assessment.bucket_1_quality}",
                    "; ".join(assessment.bucket_1_reasons),
                    _severity_for_quality(assessment.bucket_1_quality),
                )
            ),
            _decision_json(
                make_decision(
                    "evidence_quality",
                    f"bucket_2_{assessment.bucket_2_quality}",
                    "; ".join(assessment.bucket_2_reasons),
                    _severity_for_quality(assessment.bucket_2_quality),
                )
            ),
            _decision_json(
                make_decision(
                    "evidence_quality",
                    f"bucket_3_{assessment.bucket_3_quality}",
                    "; ".join(assessment.bucket_3_reasons),
                    _severity_for_quality(assessment.bucket_3_quality),
                )
            ),
        ]
    )
    return {
        "evidence_quality": assessment.model_dump(mode="json"),
        "routing_decisions": decisions,
    }


def assess_risk_tier_node(state: DodGraphState) -> DodGraphState:
    """Assess risk tier for downstream prompt strategy and final routing."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        assessment = assess_risk_tier(_load_evidence_bundle_from_state(state))
    except Exception as exc:
        return _with_error(state, "risk_tier_assessment_failed", str(exc), "routing")

    decisions = list(state.get("routing_decisions") or [])
    decisions.append(
        _decision_json(
            make_decision(
                "risk_tier",
                assessment.risk_tier,
                "; ".join(assessment.reasons),
                "warning" if assessment.risk_tier in {"medium", "high"} else "info",
                {"missing_context": assessment.missing_context},
            )
        )
    )
    return {"risk_tier": assessment.model_dump(mode="json"), "routing_decisions": decisions}


def select_prompt_strategy_node(state: DodGraphState) -> DodGraphState:
    """Select deterministic prompt strategies for each bucket."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        evidence_quality = EvidenceQualityAssessment.model_validate(state.get("evidence_quality"))
        risk_tier = RiskTierAssessment.model_validate(state.get("risk_tier"))
        strategy = select_prompt_strategy(
            evidence_quality=evidence_quality,
            risk_tier=risk_tier,
            evidence_bundle=_load_evidence_bundle_from_state(state),
        )
    except Exception as exc:
        return _with_error(state, "prompt_strategy_selection_failed", str(exc), "routing")

    decisions = list(state.get("routing_decisions") or [])
    for bucket_name, selected in (
        ("bucket_1", strategy.bucket_1_strategy),
        ("bucket_2", strategy.bucket_2_strategy),
        ("bucket_3", strategy.bucket_3_strategy),
    ):
        decisions.append(
            _decision_json(
                make_decision(
                    "prompt_strategy",
                    selected,
                    f"Selected {selected} for {bucket_name}.",
                    "info",
                )
            )
        )
    return {"prompt_strategy": strategy.model_dump(mode="json"), "routing_decisions": decisions}


def generate_llm_outputs_node(state: DodGraphState) -> DodGraphState:
    """Run Phase 5B LLM generation with bucket-level retry."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        return _generate_llm_outputs_once(state)
    except Exception as exc:
        return _with_error(state, "llm_generation_failed", str(exc), "llm_generation")


def validate_outputs_node(state: DodGraphState) -> DodGraphState:
    """Run Phase 6 validation, confidence scoring, and payload assembly."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        store = LocalJsonStore(get_settings())
        llm_outputs_path = state.get("artifact_paths", {}).get(
            "llm_outputs",
            store.output_path(state["build_id"], "llm_outputs.json"),
        )
        evidence_bundle_path = state.get("artifact_paths", {}).get(
            "evidence_bundle",
            store.evidence_path(state["build_id"], "evidence_bundle.json"),
        )
        llm_outputs = state.get("llm_outputs") or store.load_llm_outputs(state["build_id"])
        evidence_bundle = state.get("evidence_result") or store.load_evidence_bundle(
            state["build_id"]
        )
        validated = validate_and_assemble_outputs(
            build_id=state["build_id"],
            llm_outputs=llm_outputs,
            evidence_bundle=evidence_bundle,
            source_llm_outputs_path=llm_outputs_path,
            source_evidence_bundle_path=evidence_bundle_path,
            allow_llm_repair=True,
        )
        validated_payload = validated.model_dump(mode="json")
        service_now_payload = validated.service_now_payload.model_dump(mode="json")
        confidence = validated.confidence.model_dump(mode="json")
        traceability_model = getattr(validated, "traceability_report", None)
        traceability_report = (
            traceability_model.model_dump(mode="json")
            if traceability_model is not None
            else {}
        )
        validated_output_path = store.save_validated_output_json(
            state["build_id"],
            validated_payload,
        )
        service_now_payload_path = store.save_service_now_payload_json(
            state["build_id"],
            service_now_payload,
        )
        confidence_path = store.save_confidence_json(state["build_id"], confidence)
        traceability_report_path = store.save_traceability_report_json(
            state["build_id"],
            traceability_report,
        )
    except Exception as exc:
        return _with_error(state, "validation_failed", str(exc), "validation")

    warnings = list(state.get("warnings") or [])
    errors = list(state.get("errors") or [])
    validation_issue_count = 0
    validation_error_count = 0
    for item in validated_payload.get("validation_issues", []):
        if not isinstance(item, dict):
            continue
        validation_issue_count += 1
        issue = _issue(
            str(item.get("severity", "warning")),
            str(item.get("code", "validation_issue")),
            str(item.get("message", "Validation issue.")),
            "validation",
        )
        if issue["severity"] == "error":
            validation_error_count += 1
            errors.append(issue)
        else:
            warnings.append(issue)

    has_validation_errors = any(item.get("phase") == "validation" for item in errors)
    decisions = list(state.get("routing_decisions") or [])
    if validation_error_count:
        decisions.append(
            _decision_json(
                make_decision(
                    "validation",
                    "validation_errors",
                    f"Validation produced {validation_error_count} error issue(s).",
                    "warning",
                )
            )
        )
    elif validation_issue_count:
        decisions.append(
            _decision_json(
                make_decision(
                    "validation",
                    "validation_warnings",
                    f"Validation produced {validation_issue_count} non-error issue(s).",
                    "warning",
                )
            )
        )
    else:
        decisions.append(
            _decision_json(
                make_decision(
                    "validation",
                    "validation_passed",
                    "Validation completed without issues.",
                    "info",
                )
            )
        )
    if _repair_applied(validated_payload):
        decisions.append(
            _decision_json(
                make_decision(
                    "validation",
                    "repair_applied",
                    "Validation output indicates repair was applied.",
                    "info",
                )
            )
        )
    return {
        "validated_output": validated_payload,
        "service_now_payload": service_now_payload,
        "confidence": confidence,
        "artifact_paths": _merge_artifact_paths(
            state,
            {
                "validated_output": validated_output_path,
                "service_now_payload": service_now_payload_path,
                "confidence": confidence_path,
                "traceability_report": traceability_report_path,
            },
        ),
        "warnings": warnings,
        "errors": errors,
        "routing_decisions": decisions,
        "status": (
            STATUS_NEEDS_REVIEW
            if has_validation_errors
            else state.get("status", STATUS_STARTED)
        ),
    }


def assemble_run_result_node(state: DodGraphState) -> DodGraphState:
    """Determine final run status from validation, confidence, and warnings."""

    completed_at = _iso(_utc_now())
    if state.get("status") == STATUS_FAILED:
        return {"status": STATUS_FAILED, "completed_at": completed_at}

    service_now_payload = state.get("service_now_payload")
    if not service_now_payload:
        return {"status": STATUS_FAILED, "completed_at": completed_at}

    if state.get("status") == STATUS_NEEDS_REVIEW:
        return {"status": STATUS_NEEDS_REVIEW, "completed_at": completed_at}

    validation_errors = [
        item for item in state.get("errors", []) if item.get("phase") == "validation"
    ]
    if validation_errors and service_now_payload:
        return {"status": STATUS_NEEDS_REVIEW, "completed_at": completed_at}

    threshold = float(state.get("confidence_threshold") or get_settings().DOD_CONFIDENCE_THRESHOLD)
    high_risk_threshold = float(
        state.get("high_risk_confidence_threshold")
        or get_settings().DOD_HIGH_RISK_CONFIDENCE_THRESHOLD
    )
    confidence = state.get("confidence") or {}
    overall = confidence.get("overall") if isinstance(confidence, dict) else None
    risk_tier = state.get("risk_tier") or {}
    if (
        isinstance(risk_tier, dict)
        and risk_tier.get("risk_tier") == "high"
        and isinstance(overall, int | float)
        and float(overall) < high_risk_threshold
    ):
        return {"status": STATUS_NEEDS_REVIEW, "completed_at": completed_at}
    if isinstance(overall, int | float) and float(overall) < threshold:
        return {"status": STATUS_NEEDS_REVIEW, "completed_at": completed_at}

    if state.get("warnings"):
        return {"status": STATUS_COMPLETED_WITH_WARNINGS, "completed_at": completed_at}

    return {"status": STATUS_COMPLETED, "completed_at": completed_at}


def evaluate_rules_node(state: DodGraphState) -> DodGraphState:
    """Run Phase 9 deterministic post-generation rule evaluation."""

    if state.get("status") == STATUS_FAILED:
        return {}

    try:
        store = LocalJsonStore(get_settings())
        build_id = int(state["build_id"])
        evidence_bundle_path = state.get("artifact_paths", {}).get(
            "evidence_bundle",
            store.evidence_path(build_id, "evidence_bundle.json"),
        )
        service_now_payload_path = state.get("artifact_paths", {}).get(
            "service_now_payload",
            store.output_path(build_id, "service_now_payload.json"),
        )
        llm_outputs_path = state.get("artifact_paths", {}).get(
            "llm_outputs",
            store.output_path(build_id, "llm_outputs.json"),
        )
        validated_output_path = state.get("artifact_paths", {}).get(
            "validated_output",
            store.output_path(build_id, "validated_output.json"),
        )
        confidence_path = state.get("artifact_paths", {}).get(
            "confidence",
            store.output_path(build_id, "confidence.json"),
        )
        routing_path = state.get("artifact_paths", {}).get(
            "routing_decisions",
            store.output_path(build_id, "routing_decisions.json"),
        )
        traceability_path = state.get("artifact_paths", {}).get(
            "traceability_report",
            store.output_path(build_id, "traceability_report.json"),
        )
        evaluation = evaluate_rules(
            build_id=build_id,
            evidence_bundle=state.get("evidence_result") or store.load_evidence_bundle(build_id),
            service_now_payload=state.get("service_now_payload")
            or store.load_service_now_payload(build_id),
            llm_outputs=state.get("llm_outputs")
            or _load_optional_dict(store.load_llm_outputs, build_id),
            validated_output=state.get("validated_output")
            or _load_optional_dict(store.load_validated_output, build_id),
            confidence=state.get("confidence")
            or _load_optional_dict(store.load_confidence, build_id),
            routing_decisions=_routing_context_from_state(state)
            or _load_optional_dict(store.load_routing_decisions, build_id),
            traceability_report=_load_optional_dict(store.load_traceability_report, build_id),
            source_paths={
                "evidence_bundle": evidence_bundle_path,
                "service_now_payload": service_now_payload_path,
                "llm_outputs": llm_outputs_path,
                "validated_output": validated_output_path,
                "confidence": confidence_path,
                "routing_decisions": routing_path,
                "traceability_report": traceability_path,
            },
        )
        evaluation_payload = evaluation.model_dump(mode="json")
        rule_evaluation_path = store.save_rule_evaluation_json(build_id, evaluation_payload)
    except Exception as exc:
        return _with_error(state, "rule_evaluation_failed", str(exc), "rule_evaluation")

    warnings = list(state.get("warnings") or [])
    errors = list(state.get("errors") or [])
    for item in evaluation_payload.get("rules_triggered", []):
        if not isinstance(item, dict):
            continue
        issue = _issue(
            str(item.get("severity", "warning")),
            str(item.get("rule_id", "rule_triggered")),
            str(item.get("message", "Rule triggered.")),
            "rule_evaluation",
        )
        if issue["severity"] == "error":
            errors.append(issue)
        elif issue["severity"] in {"warning", "review"}:
            warnings.append(issue)

    recommended = evaluation_payload.get("summary", {}).get("recommended_status")
    status = state.get("status", STATUS_STARTED)
    if recommended == "failed":
        status = STATUS_FAILED
    elif recommended == "needs_review" and status != STATUS_FAILED:
        status = STATUS_NEEDS_REVIEW
    elif (
        recommended == "completed_with_warnings"
        and status not in {STATUS_FAILED, STATUS_NEEDS_REVIEW}
    ):
        status = STATUS_COMPLETED_WITH_WARNINGS

    return {
        "rule_evaluation": evaluation_payload,
        "artifact_paths": _merge_artifact_paths(
            state,
            {"rule_evaluation": rule_evaluation_path},
        ),
        "warnings": warnings,
        "errors": errors,
        "status": status,
    }


def persist_routing_decisions_node(state: DodGraphState) -> DodGraphState:
    """Persist Phase 7B routing decisions under data/output/{build_id}."""

    store = LocalJsonStore(get_settings())
    build_id = int(state.get("build_id") or 0)
    bundle = RoutingDecisionBundle(
        build_id=build_id,
        generated_at=_utc_now(),
        evidence_quality=_model_or_none(EvidenceQualityAssessment, state.get("evidence_quality")),
        prompt_strategy=_model_or_none(PromptStrategySelection, state.get("prompt_strategy")),
        risk_tier=_model_or_none(RiskTierAssessment, state.get("risk_tier")),
        decisions=[
            RoutingDecision.model_validate(item) for item in state.get("routing_decisions", [])
        ],
    )
    routing_path = store.save_routing_decisions_json(build_id, bundle.model_dump(mode="json"))
    return {
        "artifact_paths": _merge_artifact_paths(
            state,
            {"routing_decisions": routing_path},
        ),
        "routing_decisions_bundle": bundle.model_dump(mode="json"),
    }


def persist_run_summary_node(state: DodGraphState) -> DodGraphState:
    """Persist final run summary under data/output/{build_id}/run_summary.json."""

    store = LocalJsonStore(get_settings())
    now = _utc_now()
    started_at = _parse_datetime(state.get("started_at")) or now
    completed_at = _parse_datetime(state.get("completed_at"))
    if completed_at is None and state.get("status") == STATUS_FAILED:
        completed_at = now
    build_id = int(state.get("build_id") or 0)
    artifact_paths = dict(state.get("artifact_paths") or {})
    artifact_paths.setdefault("run_summary", store.run_summary_path(build_id))

    summary = DodRunSummary(
        run_id=str(state.get("run_id") or f"dod-run-{_timestamp_for_id(started_at)}-{build_id}"),
        build_id=build_id,
        organization=str(state.get("organization") or ""),
        project=str(state.get("project") or ""),
        status=str(state.get("status") or STATUS_FAILED),
        started_at=started_at,
        completed_at=completed_at,
        service_now_payload=state.get("service_now_payload"),
        confidence=state.get("confidence"),
        artifact_paths=artifact_paths,
        warnings=[_run_issue_from_dict(item) for item in state.get("warnings", [])],
        errors=[_run_issue_from_dict(item) for item in state.get("errors", [])],
    )
    run_summary_path = store.save_run_summary_json(build_id, summary.model_dump(mode="json"))
    artifact_paths["run_summary"] = run_summary_path

    return {
        "artifact_paths": artifact_paths,
        "completed_at": _iso(completed_at) if completed_at else state.get("completed_at"),
        "run_summary": summary.model_dump(mode="json"),
    }


def _generate_llm_outputs_once(state: DodGraphState) -> DodGraphState:
    store = LocalJsonStore(get_settings())
    evidence_bundle_path = state.get("artifact_paths", {}).get(
        "evidence_bundle",
        store.evidence_path(state["build_id"], "evidence_bundle.json"),
    )
    evidence_bundle = state.get("evidence_result") or store.load_evidence_bundle(state["build_id"])
    retry_decisions: list[dict[str, Any]] = []
    outputs = generate_all_buckets(
        build_id=state["build_id"],
        evidence_bundle=evidence_bundle,
        source_path=evidence_bundle_path,
        prompt_strategy_selection=state.get("prompt_strategy"),
        max_retries_per_bucket=1,
        on_bucket_retry=_on_bucket_retry(state, retry_decisions),
    )
    llm_payload = outputs.model_dump(mode="json")
    bucket_1_path = store.save_output_json(
        state["build_id"],
        "bucket_1_output.json",
        outputs.bucket_1.model_dump(mode="json"),
    )
    bucket_2_path = store.save_output_json(
        state["build_id"],
        "bucket_2_output.json",
        outputs.bucket_2.model_dump(mode="json"),
    )
    bucket_3_path = store.save_output_json(
        state["build_id"],
        "bucket_3_output.json",
        outputs.bucket_3.model_dump(mode="json"),
    )
    llm_outputs_path = store.save_output_json(state["build_id"], "llm_outputs.json", llm_payload)

    return {
        "llm_outputs": llm_payload,
        "artifact_paths": _merge_artifact_paths(
            state,
            {
                "bucket_1_output": bucket_1_path,
                "bucket_2_output": bucket_2_path,
                "bucket_3_output": bucket_3_path,
                "llm_outputs": llm_outputs_path,
            },
        ),
        "routing_decisions": [*list(state.get("routing_decisions") or []), *retry_decisions],
    }


def _load_evidence_bundle_from_state(state: DodGraphState) -> dict[str, Any]:
    evidence = state.get("evidence_result")
    if isinstance(evidence, dict):
        return evidence
    store = LocalJsonStore(get_settings())
    return store.load_evidence_bundle(state["build_id"])


def _load_optional_dict(load: Any, build_id: int) -> dict[str, Any] | None:
    try:
        payload = load(build_id)
    except FileNotFoundError:
        return None
    return payload if isinstance(payload, dict) else None


def _routing_context_from_state(state: DodGraphState) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if isinstance(state.get("risk_tier"), dict):
        payload["risk_tier"] = state["risk_tier"]
    decisions = state.get("routing_decisions")
    if isinstance(decisions, list):
        payload["decisions"] = decisions
    return payload or None


def _severity_for_quality(quality: str) -> str:
    if quality == "weak":
        return "warning"
    return "info"


def _decision_json(decision: RoutingDecision) -> dict[str, Any]:
    return decision.model_dump(mode="json")


def _repair_applied(validated_payload: dict[str, Any]) -> bool:
    results = validated_payload.get("bucket_validation_results")
    if not isinstance(results, list):
        return False
    return any(isinstance(item, dict) and item.get("repaired") is True for item in results)


def _on_bucket_retry(
    state: DodGraphState,
    retry_decisions: list[dict[str, Any]],
) -> Any:
    def record_retry(bucket_name: str, attempt: int, exc: Exception) -> None:
        _ = state
        retry_decisions.append(
            _decision_json(
                make_decision(
                    "llm_generation",
                    f"{bucket_name}_retry",
                    f"Retrying {bucket_name} after failed attempt {attempt}: {exc}",
                    "warning",
                    {"bucket": bucket_name, "attempt": attempt},
                )
            )
        )

    return record_retry


def _model_or_none(model_type: Any, payload: Any) -> Any:
    if payload is None:
        return None
    return model_type.model_validate(payload)


def _with_error(state: DodGraphState, code: str, message: str, phase: str) -> DodGraphState:
    return {
        "status": STATUS_FAILED,
        "errors": [*list(state.get("errors") or []), _issue("error", code, message, phase)],
    }


def _merge_artifact_paths(state: DodGraphState, updates: dict[str, str]) -> dict[str, str]:
    existing = dict(state.get("artifact_paths") or {})
    for key, value in updates.items():
        if value:
            existing[key] = value
    return existing


def _extract_paths(value: Any) -> dict[str, str]:
    payload = _model_dump(value)
    if not isinstance(payload, dict):
        return {}
    return {str(key): str(item) for key, item in payload.items() if item}


def _collector_issue(payload: Any, phase: str) -> dict[str, Any]:
    if isinstance(payload, dict):
        collector = str(payload.get("collector", "collector"))
        message = str(payload.get("message", "Collector issue."))
        return _issue("warning", f"{collector}_issue", message, phase)
    return _issue("warning", "collector_issue", str(payload), phase)


def _warnings_from_strings(values: list[Any], phase: str, code: str) -> list[dict[str, Any]]:
    return [_issue("warning", code, str(value), phase) for value in values]


def _issue(severity: str, code: str, message: str, phase: str | None) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "phase": phase,
    }


def _run_issue_from_dict(payload: dict[str, Any]) -> RunIssue:
    return RunIssue(
        severity=str(payload.get("severity") or "warning"),
        code=str(payload.get("code") or "unknown_issue"),
        message=str(payload.get("message") or payload.get("code") or "Issue recorded."),
        phase=payload.get("phase") if isinstance(payload.get("phase"), str) else None,
    )


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _coerce_build_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _coerce_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _timestamp_for_id(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return cast(datetime, datetime.fromisoformat(value.replace("Z", "+00:00")))
    except ValueError:
        return None
