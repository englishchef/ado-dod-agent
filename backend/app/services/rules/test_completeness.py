"""Test evidence completeness scoring and rules."""

from __future__ import annotations

from typing import Any

from backend.app.models.rules import RuleResult, TestCompletenessScore

_TEST_TERMS = ("test", "functional", "regression", "unit", "integration", "validation")
_NONFUNCTIONAL_TERMS = ("performance", "load", "reliability", "stress")
_SECURITY_TERMS = ("security", "sast", "sca", "container scan", "vulnerability", "scan")
_COVERAGE_TERMS = ("coverage", "quality gate", "code quality")
_DEPLOYMENT_VALIDATION_TERMS = (
    "smoke",
    "health",
    "monitoring",
    "synthetic",
    "deployment validation",
    "validate",
)


def calculate_test_completeness_score(
    evidence_bundle: dict[str, Any],
    service_now_payload: dict[str, Any],
    validated_output: dict[str, Any] | None = None,
    routing_decisions: dict[str, Any] | None = None,
    traceability_report: dict[str, Any] | None = None,
) -> TestCompletenessScore:
    """Calculate deterministic completeness score for test and validation evidence."""

    _ = service_now_payload, validated_output, routing_decisions
    functional = 0.0
    if has_test_results(evidence_bundle):
        functional += 0.65
    if _has_text_signal(evidence_bundle, _TEST_TERMS):
        functional += 0.25
    if _task_has_terms(evidence_bundle, _TEST_TERMS):
        functional += 0.10
    functional = min(functional, 1.0)

    nonfunctional = 1.0 if _has_text_signal(evidence_bundle, _NONFUNCTIONAL_TERMS) else 0.0
    coverage = 1.0 if _has_text_signal(evidence_bundle, _COVERAGE_TERMS) else 0.0
    security = 1.0 if has_security_scan_signals(evidence_bundle) else 0.0
    deployment = 0.0
    if has_validation_signals(evidence_bundle):
        deployment += 0.65
    if has_artifact_evidence(evidence_bundle):
        deployment += 0.20
    if _task_has_terms(evidence_bundle, _DEPLOYMENT_VALIDATION_TERMS):
        deployment += 0.15
    deployment = min(deployment, 1.0)
    traceability = 1.0 if has_traceability(traceability_report) else 0.0

    if has_failed_tests(evidence_bundle):
        functional = min(functional, 0.35)
    if has_skipped_test_stage(evidence_bundle):
        functional = min(functional, 0.40)
        deployment = min(deployment, 0.50)

    overall = (
        functional * 0.25
        + nonfunctional * 0.20
        + coverage * 0.15
        + security * 0.15
        + deployment * 0.15
        + traceability * 0.10
    )
    if not has_test_results(evidence_bundle) and not has_validation_signals(evidence_bundle):
        overall = min(overall, 0.30)
    if not has_test_results(evidence_bundle) and has_validation_signals(evidence_bundle):
        overall = max(overall, 0.35)
        overall = min(overall, 0.60)
    if has_failed_tests(evidence_bundle):
        overall = min(overall, 0.55)

    missing: list[str] = []
    if not has_test_results(evidence_bundle):
        missing.append("automated test results")
    if not _has_text_signal(evidence_bundle, _NONFUNCTIONAL_TERMS):
        missing.append("non-functional test evidence")
    if not _has_text_signal(evidence_bundle, _COVERAGE_TERMS):
        missing.append("coverage or code quality evidence")
    if not has_security_scan_signals(evidence_bundle):
        missing.append("security scan evidence")
    if not has_validation_signals(evidence_bundle):
        missing.append("deployment validation signals")
    if not has_traceability(traceability_report):
        missing.append("field traceability references")

    rationale = [
        f"functional={functional:.2f}",
        f"nonfunctional={nonfunctional:.2f}",
        f"coverage={coverage:.2f}",
        f"security={security:.2f}",
        f"deployment_validation={deployment:.2f}",
        f"traceability={traceability:.2f}",
    ]
    return TestCompletenessScore(
        overall_score=round(overall, 4),
        functional_score=round(functional, 4),
        nonfunctional_score=round(nonfunctional, 4),
        coverage_score=round(coverage, 4),
        security_score=round(security, 4),
        deployment_validation_score=round(deployment, 4),
        traceability_score=round(traceability, 4),
        rationale=rationale,
        missing_evidence=missing,
    )


def evaluate_test_completeness_rules(
    evidence_bundle: dict[str, Any],
    score: TestCompletenessScore,
    validated_output: dict[str, Any] | None = None,
) -> list[RuleResult]:
    """Evaluate deterministic test completeness rules."""

    rules: list[RuleResult] = []
    if not has_test_results(evidence_bundle) and not has_validation_signals(evidence_bundle):
        rules.append(
            _rule(
                "TEST_NO_AUTOMATED_RESULTS",
                "review",
                "No automated test results or validation signals were found.",
            )
        )
    if has_skipped_test_stage(evidence_bundle):
        rules.append(
            _rule(
                "TEST_STAGE_SKIPPED",
                "review",
                "A test-related stage, job, or task appears to have been skipped.",
            )
        )
    if has_failed_tests(evidence_bundle):
        severity = "error" if _validated_blocks_failed_tests(validated_output) else "review"
        rules.append(_rule("TEST_FAILURES_PRESENT", severity, "Failed test evidence is present."))
    if not _has_text_signal(evidence_bundle, _TEST_TERMS) and not has_test_results(evidence_bundle):
        severity = "review" if score.overall_score <= 0.30 else "warning"
        rules.append(
            _rule(
                "NO_FUNCTIONAL_TEST_EVIDENCE",
                severity,
                "Functional test evidence was not found.",
            )
        )
    if not _has_text_signal(evidence_bundle, _NONFUNCTIONAL_TERMS + _SECURITY_TERMS):
        rules.append(
            _rule(
                "NO_NONFUNCTIONAL_TEST_EVIDENCE",
                "warning",
                "Non-functional test evidence was not found.",
            )
        )
    if not _has_text_signal(evidence_bundle, _COVERAGE_TERMS):
        rules.append(
            _rule(
                "NO_COVERAGE_EVIDENCE",
                "info",
                "Coverage or code quality evidence was not found.",
            )
        )
    if _has_failed_signal(evidence_bundle, _SECURITY_TERMS):
        rules.append(
            _rule(
                "SCAN_FAILED",
                "review",
                "A security or quality scan appears to have failed.",
            )
        )
    if _has_failed_signal(evidence_bundle, ("quality gate",)):
        rules.append(_rule("QUALITY_GATE_FAILED", "review", "A quality gate failure was detected."))
    return rules


def has_test_results(evidence_bundle: dict[str, Any]) -> bool:
    test_evidence = _bucket(evidence_bundle, "bucket_2").get("test_evidence")
    if not isinstance(test_evidence, dict):
        return False
    return any(
        int(test_evidence.get(key) or 0) > 0
        for key in ("total_runs", "total_tests", "passed_tests", "failed_tests", "skipped_tests")
    )


def has_failed_tests(evidence_bundle: dict[str, Any]) -> bool:
    test_evidence = _bucket(evidence_bundle, "bucket_2").get("test_evidence")
    if isinstance(test_evidence, dict) and int(test_evidence.get("failed_tests") or 0) > 0:
        return True
    return bool(_bucket(evidence_bundle, "bucket_3").get("failed_or_warning_evidence"))


def has_skipped_test_stage(evidence_bundle: dict[str, Any]) -> bool:
    for item in _timeline_items(evidence_bundle):
        text = _item_text(item)
        if any(term in text for term in _TEST_TERMS) and any(
            state in text for state in ("skipped", "canceled", "cancelled")
        ):
            return True
    return False


def has_validation_signals(evidence_bundle: dict[str, Any]) -> bool:
    bucket_2 = _bucket(evidence_bundle, "bucket_2")
    for key in ("validation_signals", "deployment_signals", "quality_signals"):
        if bucket_2.get(key):
            return True
    return _task_has_terms(evidence_bundle, _DEPLOYMENT_VALIDATION_TERMS)


def has_security_scan_signals(evidence_bundle: dict[str, Any]) -> bool:
    return _has_text_signal(evidence_bundle, _SECURITY_TERMS)


def has_artifact_evidence(evidence_bundle: dict[str, Any]) -> bool:
    return bool(_bucket(evidence_bundle, "bucket_2").get("artifact_evidence")) or bool(
        _bucket(evidence_bundle, "bucket_3").get("artifact_evidence")
    )


def has_traceability(traceability_report: dict[str, Any] | None) -> bool:
    if not isinstance(traceability_report, dict):
        return False
    field_traceability = traceability_report.get("field_traceability")
    if not isinstance(field_traceability, dict):
        return False
    for item in field_traceability.values():
        if isinstance(item, dict) and item.get("friendly_refs"):
            return True
    return False


def _rule(rule_id: str, severity: str, message: str) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="test_completeness",
        severity=severity,  # type: ignore[arg-type]
        message=message,
    )


def _bucket(evidence_bundle: dict[str, Any], name: str) -> dict[str, Any]:
    value = evidence_bundle.get(name)
    return value if isinstance(value, dict) else {}


def _timeline_items(evidence_bundle: dict[str, Any]) -> list[Any]:
    bucket_2 = _bucket(evidence_bundle, "bucket_2")
    return [
        *list(bucket_2.get("stage_evidence") or []),
        *list(bucket_2.get("job_evidence") or []),
        *list(bucket_2.get("task_evidence") or []),
    ]


def _item_text(item: Any) -> str:
    if isinstance(item, dict):
        return " ".join(str(value).lower() for value in item.values())
    return str(item).lower()


def _all_text(evidence_bundle: dict[str, Any]) -> str:
    return str(evidence_bundle).lower()


def _has_text_signal(evidence_bundle: dict[str, Any], terms: tuple[str, ...]) -> bool:
    text = _all_text(evidence_bundle)
    return any(term in text for term in terms)


def _task_has_terms(evidence_bundle: dict[str, Any], terms: tuple[str, ...]) -> bool:
    return any(
        any(term in _item_text(item) for term in terms)
        for item in _timeline_items(evidence_bundle)
    )


def _has_failed_signal(evidence_bundle: dict[str, Any], terms: tuple[str, ...]) -> bool:
    text = _all_text(evidence_bundle)
    return any(term in text for term in terms) and any(
        marker in text for marker in ("failed", "failure", "not passed")
    )


def _validated_blocks_failed_tests(validated_output: dict[str, Any] | None) -> bool:
    if not isinstance(validated_output, dict):
        return False
    issues = validated_output.get("validation_issues")
    if not isinstance(issues, list):
        return False
    return any(
        isinstance(item, dict)
        and item.get("code") == "unsupported_test_claim"
        and item.get("severity") == "error"
        for item in issues
    )
