"""Risk and impact consistency rules."""

from __future__ import annotations

from typing import Any

from backend.app.models.rules import RuleResult, TestCompletenessScore

_DB_TERMS = ("data", "schema", "database", "migration", "sql", "persistence", "rollback")
_INFRA_TERMS = (
    "platform",
    "infrastructure",
    "environment",
    "aks",
    "container",
    "network",
    "deployment platform",
)
_DEPENDENCY_TERMS = (
    "dependency",
    "package",
    "compatibility",
    "vulnerability",
    "library",
    "version",
    "runtime",
)
_CONFIG_TERMS = ("configuration", "environment", "settings", "variable", "secret", "config")
_FEATURE_FLAG_TERMS = ("feature flag", "toggle", "enable", "disable", "controlled rollout")


def evaluate_risk_rules(
    service_now_payload: dict[str, Any],
    evidence_bundle: dict[str, Any],
    routing_decisions: dict[str, Any] | None = None,
    confidence: dict[str, Any] | None = None,
    test_completeness_score: TestCompletenessScore | None = None,
) -> list[RuleResult]:
    """Evaluate risk and impact consistency rules."""

    risk_text = str(service_now_payload.get("risk_impact_analysis") or "").lower()
    flags = _risk_flags(evidence_bundle)
    rules: list[RuleResult] = []
    if flags.get("database_change_detected") is True and not _mentions(risk_text, _DB_TERMS):
        rules.append(
            _rule(
                "DB_CHANGE_RISK_MISSING",
                "review",
                "Database risk flag is present but database impact is not discussed.",
            )
        )
    if flags.get("infrastructure_change_detected") is True and not _mentions(
        risk_text, _INFRA_TERMS
    ):
        rules.append(
            _rule(
                "INFRA_CHANGE_RISK_MISSING",
                "review",
                "Infrastructure risk flag is present but platform impact is not discussed.",
            )
        )
    if flags.get("dependency_change_detected") is True and not _mentions(
        risk_text, _DEPENDENCY_TERMS
    ):
        rules.append(
            _rule(
                "DEPENDENCY_RISK_MISSING",
                "warning",
                "Dependency risk flag is present but compatibility impact is not discussed.",
            )
        )
    if flags.get("config_change_detected") is True and not _mentions(risk_text, _CONFIG_TERMS):
        rules.append(
            _rule(
                "CONFIG_RISK_MISSING",
                "warning",
                "Configuration risk flag is present but settings impact is not discussed.",
            )
        )
    if flags.get("feature_flag_change_detected") is True and not _mentions(
        risk_text, _FEATURE_FLAG_TERMS
    ):
        rules.append(
            _rule(
                "FEATURE_FLAG_RISK_MISSING",
                "warning",
                "Feature flag risk flag is present but rollout or fallback is not discussed.",
            )
        )
    if _risk_tier(routing_decisions) == "high":
        weak_tests = (
            test_completeness_score is not None
            and test_completeness_score.overall_score < 0.50
        )
        overall_confidence = _overall_confidence(confidence)
        low_confidence = overall_confidence is not None and overall_confidence < 0.85
        if weak_tests or low_confidence:
            rules.append(
                _rule(
                    "HIGH_RISK_WEAK_VALIDATION",
                    "review",
                    "High risk routing is paired with weak validation or confidence.",
                )
            )
    return rules


def _rule(rule_id: str, severity: str, message: str) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="risk_impact",
        severity=severity,  # type: ignore[arg-type]
        message=message,
        field_name="risk_impact_analysis",
    )


def _mentions(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _risk_flags(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    bucket = evidence_bundle.get("bucket_3")
    if isinstance(bucket, dict) and isinstance(bucket.get("risk_flags"), dict):
        return dict(bucket["risk_flags"])
    return {}


def _risk_tier(routing_decisions: dict[str, Any] | None) -> str | None:
    if not isinstance(routing_decisions, dict):
        return None
    risk_tier = routing_decisions.get("risk_tier")
    if isinstance(risk_tier, dict) and isinstance(risk_tier.get("risk_tier"), str):
        return str(risk_tier["risk_tier"])
    return None


def _overall_confidence(confidence: dict[str, Any] | None) -> float | None:
    if not isinstance(confidence, dict):
        return None
    value = confidence.get("overall")
    return float(value) if isinstance(value, int | float) else None
