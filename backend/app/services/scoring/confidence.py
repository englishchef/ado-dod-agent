"""Hybrid deterministic/model confidence scoring for Phase 6."""

from __future__ import annotations

from typing import Any

from backend.app.models.llm_outputs import CombinedLlmOutputs
from backend.app.models.validated_outputs import ConfidenceScore, ValidationIssue


def score_confidence(
    llm_outputs: CombinedLlmOutputs | dict[str, Any],
    evidence_bundle: dict[str, Any],
    validation_issues: list[ValidationIssue],
) -> ConfidenceScore:
    """Score final confidence using evidence strength, issues, and model confidence."""

    outputs = _as_dict(llm_outputs)
    bucket_scores: dict[str, float] = {}
    rationale: dict[str, list[str]] = {}
    for bucket in ("bucket_1", "bucket_2", "bucket_3"):
        deterministic, reasons = _deterministic_bucket_score(
            bucket,
            outputs,
            evidence_bundle,
            validation_issues,
        )
        model_confidence = _model_confidence(outputs, bucket)
        final = _clamp((0.70 * deterministic) + (0.30 * model_confidence))
        reasons.append(f"Model confidence contribution: {model_confidence:.2f}.")
        bucket_scores[bucket] = final
        rationale[bucket] = reasons

    overall = sum(bucket_scores.values()) / 3
    if any(issue.severity == "error" for issue in validation_issues):
        overall -= 0.05
    overall = _clamp(overall)
    rationale["overall"] = ["Overall score is the average of bucket scores."]
    if any(issue.severity == "error" for issue in validation_issues):
        rationale["overall"].append("Overall score reduced because validation errors exist.")

    return ConfidenceScore(
        overall=overall,
        bucket_1=bucket_scores["bucket_1"],
        bucket_2=bucket_scores["bucket_2"],
        bucket_3=bucket_scores["bucket_3"],
        rationale=rationale,
    )


def _deterministic_bucket_score(
    bucket: str,
    outputs: dict[str, Any],
    evidence_bundle: dict[str, Any],
    issues: list[ValidationIssue],
) -> tuple[float, list[str]]:
    score = 0.70
    reasons = ["Baseline deterministic score starts at 0.70."]
    evidence = _bucket(evidence_bundle, bucket)
    output = _bucket(outputs, bucket)

    if bucket == "bucket_1":
        score = _adjust(
            score,
            bool(evidence.get("work_item_evidence")),
            0.10,
            -0.10,
            reasons,
            "work item evidence",
        )
        score = _adjust(
            score, bool(evidence.get("commit_evidence")), 0.10, 0.0, reasons, "commit evidence"
        )
        score = _adjust(
            score, bool(evidence.get("pull_request_evidence")), 0.05, -0.05, reasons, "PR metadata"
        )
        if _has_acceptance_or_business_value(evidence):
            score += 0.05
            reasons.append("Acceptance criteria or business value evidence is present.")
    elif bucket == "bucket_2":
        has_stage_or_task = bool(evidence.get("stage_evidence") or evidence.get("task_evidence"))
        score = _adjust(score, has_stage_or_task, 0.10, 0.0, reasons, "stage/task evidence")
        score = _adjust(
            score, bool(evidence.get("artifact_evidence")), 0.10, 0.0, reasons, "artifact evidence"
        )
        tests_exist = _test_results_exist(evidence)
        score = _adjust(score, tests_exist, 0.10, -0.15, reasons, "test results")
        score = _adjust(
            score,
            bool(evidence.get("validation_signals")),
            0.05,
            0.0,
            reasons,
            "validation signals",
        )
        if not evidence.get("deployment_signals"):
            score -= 0.10
            reasons.append("Deployment signals are missing.")
    elif bucket == "bucket_3":
        score = _adjust(
            score,
            bool(evidence.get("artifact_evidence")),
            0.10,
            -0.10,
            reasons,
            "artifact evidence",
        )
        score = _adjust(
            score,
            bool(evidence.get("rollback_indicators")),
            0.10,
            -0.10,
            reasons,
            "rollback indicators",
        )
        score = _adjust(
            score,
            bool(evidence.get("impacted_components")),
            0.05,
            0.0,
            reasons,
            "impacted components",
        )
        score = _adjust(score, bool(evidence.get("risk_flags")), 0.05, 0.0, reasons, "risk flags")
        if _test_context_missing(evidence_bundle):
            score -= 0.10
            reasons.append("Missing test context increases rollback/risk uncertainty.")

    if not output.get("evidence_used"):
        score -= 0.10
        reasons.append("Generated output has no evidence_used references.")

    warning_count = sum(
        1 for issue in issues if issue.bucket == bucket and issue.severity == "warning"
    )
    error_count = sum(1 for issue in issues if issue.bucket == bucket and issue.severity == "error")
    warning_penalty = min(warning_count * 0.05, 0.20)
    error_penalty = min(error_count * 0.20, 0.40)
    score -= warning_penalty + error_penalty
    if warning_count:
        reasons.append(f"Validation warnings reduce score by {warning_penalty:.2f}.")
    if error_count:
        reasons.append(f"Validation errors reduce score by {error_penalty:.2f}.")
    return _clamp(score), reasons


def _adjust(
    score: float,
    present: bool,
    bonus: float,
    penalty: float,
    reasons: list[str],
    label: str,
) -> float:
    if present:
        reasons.append(f"{label.capitalize()} is present.")
        return score + bonus
    if penalty:
        reasons.append(f"{label.capitalize()} is missing.")
        return score + penalty
    return score


def _as_dict(llm_outputs: CombinedLlmOutputs | dict[str, Any]) -> dict[str, Any]:
    if isinstance(llm_outputs, CombinedLlmOutputs):
        return llm_outputs.model_dump(mode="json")
    return llm_outputs


def _bucket(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    return value if isinstance(value, dict) else {}


def _model_confidence(outputs: dict[str, Any], bucket: str) -> float:
    value = _bucket(outputs, bucket).get("model_confidence", 0.5)
    return _clamp(float(value)) if isinstance(value, (int, float)) else 0.5


def _test_results_exist(bucket_2: dict[str, Any]) -> bool:
    test_evidence = bucket_2.get("test_evidence")
    return isinstance(test_evidence, dict) and int(test_evidence.get("total_tests") or 0) > 0


def _test_context_missing(evidence_bundle: dict[str, Any]) -> bool:
    test_evidence = _bucket(evidence_bundle, "bucket_2").get("test_evidence")
    if not isinstance(test_evidence, dict):
        return True
    return (
        bool(test_evidence.get("missing_test_context"))
        or int(test_evidence.get("total_tests") or 0) == 0
    )


def _has_acceptance_or_business_value(bucket_1: dict[str, Any]) -> bool:
    for item in bucket_1.get("work_item_evidence", []):
        if isinstance(item, dict) and (
            item.get("acceptance_criteria") or item.get("business_value")
        ):
            return True
    return False


def _clamp(value: float) -> float:
    return max(0.0, min(value, 1.0))
