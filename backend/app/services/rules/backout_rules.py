"""Backout plan quality rules."""

from __future__ import annotations

from typing import Any

from backend.app.models.rules import RuleResult
from backend.app.services.validation.output_validator import validate_bucket_3_fields

_ROLLBACK_ANCHORS = (
    "previous version",
    "previous known-good",
    "previously validated",
    "known-good",
    "pre-change state",
    "prior state",
    "redeploy",
    "revert",
    "restore",
)
_REVERSAL_TERMS = (
    "redeploy the previous",
    "redeploy the previously",
    "rollback",
    "revert",
    "disable feature",
    "restore prior",
    "restore the prior",
    "pre-change state",
)
_DB_BACKOUT_TERMS = (
    "db rollback",
    "database rollback",
    "migration rollback",
    "schema rollback",
    "data restore",
    "backup",
    "migration",
)
_INFRA_BACKOUT_TERMS = (
    "infrastructure rollback",
    "iac rollback",
    "configuration rollback",
    "platform rollback",
    "infrastructure revert",
    "config revert",
)


def evaluate_backout_rules(
    service_now_payload: dict[str, Any],
    evidence_bundle: dict[str, Any],
    traceability_report: dict[str, Any] | None = None,
) -> list[RuleResult]:
    """Evaluate backout plan quality rules."""

    _ = traceability_report
    backout = str(service_now_payload.get("backout_plan") or "").lower()
    risk_flags = _risk_flags(evidence_bundle)
    rules: list[RuleResult] = []
    if not any(term in backout for term in _ROLLBACK_ANCHORS):
        rules.append(
            _rule(
                "BACKOUT_NO_ROLLBACK_ANCHOR",
                "review",
                "Backout plan does not include a rollback anchor.",
                "backout_plan",
            )
        )
    if not any(term in backout for term in _REVERSAL_TERMS):
        rules.append(
            _rule(
                "BACKOUT_NO_DEPLOYMENT_REVERSAL",
                "warning",
                "Backout plan does not include a clear deployment reversal action.",
                "backout_plan",
            )
        )
    if risk_flags.get("database_change_detected") is True and not any(
        term in backout for term in _DB_BACKOUT_TERMS
    ):
        rules.append(
            _rule(
                "DB_CHANGE_NO_DB_BACKOUT",
                "review",
                "Database change risk is present but DB backout is not covered.",
                "backout_plan",
            )
        )
    if risk_flags.get("infrastructure_change_detected") is True and not any(
        term in backout for term in _INFRA_BACKOUT_TERMS
    ):
        rules.append(
            _rule(
                "INFRA_CHANGE_NO_INFRA_BACKOUT",
                "review",
                "Infrastructure change risk is present but infra backout is not covered.",
                "backout_plan",
            )
        )
    rollback_claimed = any(
        term in backout for term in ("rollback tested", "backout tested", "rollback validated")
    )
    if rollback_claimed and not _rollback_supported(evidence_bundle):
        rules.append(
            _rule(
                "BACKOUT_CLAIMS_TESTED_WITHOUT_EVIDENCE",
                "review",
                "Backout plan claims rollback testing without supporting evidence.",
                "backout_plan",
            )
        )
    existing_rule_ids = {rule.rule_id for rule in rules}
    for issue in validate_bucket_3_fields(service_now_payload, evidence_bundle):
        if issue.field != "backout_plan" or issue.code in existing_rule_ids:
            continue
        rules.append(
            _rule(
                issue.code,
                "review"
                if issue.code
                in {
                    "BACKOUT_PLAN_DELIVERY_METADATA_LEAKAGE",
                    "BACKOUT_DURATION_UNSUPPORTED",
                }
                else "warning",
                issue.message,
                "backout_plan",
            )
        )
        existing_rule_ids.add(issue.code)
    return rules


def _rule(rule_id: str, severity: str, message: str, field_name: str) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        category="backout_plan",
        severity=severity,  # type: ignore[arg-type]
        message=message,
        field_name=field_name,
    )


def _risk_flags(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    bucket = evidence_bundle.get("bucket_3")
    if isinstance(bucket, dict) and isinstance(bucket.get("risk_flags"), dict):
        return dict(bucket["risk_flags"])
    return {}


def _rollback_supported(evidence_bundle: dict[str, Any]) -> bool:
    text = str(evidence_bundle).lower()
    return any(term in text for term in ("rollback tested", "rollback validated", "backout tested"))
