"""Focused tests for concise, evidence-grounded Bucket 3 ServiceNow fields."""

from __future__ import annotations

from typing import Any

from backend.app.services.formatting.servicenow_formatter import (
    SERVICE_NOW_FIELD_NAMES,
    format_service_now_payload,
)
from backend.app.services.validation.output_repair import repair_bucket_3_fields
from backend.app.services.validation.output_validator import validate_bucket_3_fields


def _evidence(
    *,
    duration_seconds: float | None = 900,
    activities: list[dict[str, Any]] | None = None,
    resiliency: dict[str, Any] | None = None,
    planned_impact: list[str] | None = None,
    high_risk: list[str] | None = None,
    application_candidates: list[str] | None = None,
    repository_name: str | None = "contact-center-asac",
    risk_flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    if activities is None:
        activities = [
            {"name": "Deploy solution package", "duration_seconds": 480},
            {"name": "Update environment configuration", "duration_seconds": 180},
            {"name": "Validate application health", "duration_seconds": 240},
        ]
    return {
        "bucket_3": {
            "service_context": {"repository_name": repository_name},
            "uat_deployment": {
                "stage_name": "UAT",
                "activities": activities,
                "total_deployment_duration_seconds": duration_seconds,
            },
            "resiliency_evidence": resiliency or {},
            "planned_impact_evidence": planned_impact or [],
            "high_risk_evidence": high_risk or [],
            "application_candidates": (
                ["Contact Center ASAC application"]
                if application_candidates is None
                else application_candidates
            ),
            "rollback_indicators": ["UAT deployment activities"],
            "risk_flags": risk_flags or {},
            "risk_signals": [],
        }
    }


def _repair(evidence: dict[str, Any]) -> dict[str, Any]:
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": (
                "Use build 123 and artifact name drop to roll back through the pipeline."
            ),
            "risk_impact_analysis": "A broad worst-case risk narrative.",
        },
        evidence,
    )
    return repaired


def _risk_text(likelihood: str) -> str:
    return (
        "Planned impact: No planned service outage is identified.\n\n"
        "Impacted application: Contact Center ASAC application.\n\n"
        f"Likelihood of unplanned impact: {likelihood}.\n\n"
        "Potential impact: The application may experience temporary functional degradation."
    )


def test_backout_uses_uat_solution_and_configuration_reverse_steps() -> None:
    backout = str(_repair(_evidence())["backout_plan"])

    assert "Redeploy the previously validated solution" in backout
    assert "Restore the prior application configuration" in backout
    assert "Validate the impacted application" in backout
    assert "pipeline" not in backout.lower()
    assert "build" not in backout.lower()
    assert "artifact" not in backout.lower()


def test_backout_rounds_observed_uat_duration_to_practical_estimate() -> None:
    backout = str(_repair(_evidence(duration_seconds=900))["backout_plan"])

    assert "Estimated backout time: approximately 20 minutes." in backout


def test_backout_without_uat_timing_requires_confirmation() -> None:
    backout = str(_repair(_evidence(duration_seconds=None))["backout_plan"])

    assert (
        "Estimated backout time: To be confirmed by the implementation team before change "
        "execution."
    ) in backout
    assert "approximately 20 minutes" not in backout


def test_backout_metadata_is_flagged_and_removed_by_repair() -> None:
    generated = (
        "1. Redeploy last known stable build 1.0.0.590 using artifact name drop.\n"
        "2. Run the release pipeline from the main branch.\n\n"
        "Estimated backout time: approximately 20 minutes."
    )
    issues = validate_bucket_3_fields(
        {"backout_plan": generated, "risk_impact_analysis": _risk_text("Possible")},
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {"backout_plan": generated, "risk_impact_analysis": _risk_text("Possible")},
        _evidence(),
    )

    assert any(issue.code == "BACKOUT_PLAN_DELIVERY_METADATA_LEAKAGE" for issue in issues)
    repaired_backout = str(repaired["backout_plan"]).lower()
    assert "1.0.0.590" not in repaired_backout
    assert "artifact name" not in repaired_backout
    assert "pipeline" not in repaired_backout
    assert "main branch" not in repaired_backout


def test_long_backout_narrative_is_repaired_to_concise_numbered_steps() -> None:
    narrative = " ".join(
        [
            "The implementation team will coordinate with stakeholders before reviewing the "
            "general operational situation and deciding how to proceed."
        ]
        * 12
    )
    issues = validate_bucket_3_fields(
        {"backout_plan": narrative, "risk_impact_analysis": _risk_text("Possible")},
        _evidence(),
    )
    repaired, _ = repair_bucket_3_fields(
        {"backout_plan": narrative, "risk_impact_analysis": _risk_text("Possible")},
        _evidence(),
    )

    assert any(issue.code == "BACKOUT_PLAN_MISSING_STEPS" for issue in issues)
    assert any(issue.code == "BACKOUT_PLAN_TOO_VERBOSE" for issue in issues)
    backout = str(repaired["backout_plan"])
    assert backout.startswith("1. ")
    assert "stakeholder" not in backout.lower()


def test_no_outage_evidence_defaults_to_no_planned_service_outage() -> None:
    risk = str(_repair(_evidence())["risk_impact_analysis"])

    assert "Planned impact: No planned service outage is identified." in risk


def test_explicit_outage_evidence_is_preserved_without_invention() -> None:
    supported = "Contact Center ASAC application will be unavailable for approximately 15 minutes."
    risk = str(_repair(_evidence(planned_impact=[supported]))["risk_impact_analysis"])

    assert f"Planned impact: {supported}" in risk
    assert "15 minutes" in risk


def test_unsupported_planned_outage_is_flagged_and_repaired_to_no_identified_outage() -> None:
    unsupported = _risk_text("Possible").replace(
        "No planned service outage is identified",
        "The application will be unavailable for 30 minutes",
    )
    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": unsupported,
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": unsupported,
        },
        _evidence(),
    )

    assert any(issue.code == "RISK_IMPACT_SPECULATIVE" for issue in issues)
    assert "Planned impact: No planned service outage is identified." in str(
        repaired["risk_impact_analysis"]
    )


def test_possible_is_default_without_resiliency_or_high_risk_evidence() -> None:
    risk = str(_repair(_evidence())["risk_impact_analysis"])

    assert "Likelihood of unplanned impact: Possible." in risk


def test_explicit_rolling_or_secondary_region_evidence_allows_improbable() -> None:
    risk = str(
        _repair(
            _evidence(
                resiliency={
                    "rolling_deployment": True,
                    "alternate_region": "Traffic remains on the active secondary region.",
                }
            )
        )["risk_impact_analysis"]
    )

    assert "Likelihood of unplanned impact: Improbable." in risk


def test_improbable_without_resiliency_is_flagged_and_repaired_to_possible() -> None:
    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": _risk_text("Improbable"),
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": _risk_text("Improbable"),
        },
        _evidence(),
    )

    assert any(issue.code == "IMPROBABLE_WITHOUT_RESILIENCY_EVIDENCE" for issue in issues)
    assert "Likelihood of unplanned impact: Possible." in str(repaired["risk_impact_analysis"])


def test_probable_without_high_risk_evidence_is_flagged_and_repaired_to_possible() -> None:
    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": _risk_text("Probable"),
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": _risk_text("Probable"),
        },
        _evidence(),
    )

    assert any(issue.code == "PROBABLE_WITHOUT_HIGH_RISK_EVIDENCE" for issue in issues)
    assert "Likelihood of unplanned impact: Possible." in str(repaired["risk_impact_analysis"])


def test_explicit_recurring_failure_evidence_allows_probable() -> None:
    risk = str(
        _repair(
            _evidence(
                high_risk=["Known recurring deployment failures affected this application."]
            )
        )["risk_impact_analysis"]
    )

    assert "Likelihood of unplanned impact: Probable." in risk


def test_repository_name_becomes_business_readable_application_name() -> None:
    risk = str(
        _repair(
            _evidence(
                application_candidates=[],
                repository_name="contact-center-asac",
            )
        )["risk_impact_analysis"]
    )

    assert "Impacted application: Contact Center ASAC application." in risk


def test_unsupported_data_loss_claim_is_flagged_and_removed() -> None:
    speculative = _risk_text("Possible").replace(
        "temporary functional degradation",
        "database corruption and data loss",
    ) + " The release pipeline will redeploy the artifact."
    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": speculative,
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": speculative,
        },
        _evidence(),
    )

    assert any(issue.code == "RISK_IMPACT_SPECULATIVE" for issue in issues)
    repaired_risk = str(repaired["risk_impact_analysis"]).lower()
    assert "data loss" not in repaired_risk
    assert "database corruption" not in repaired_risk
    assert "pipeline" not in repaired_risk
    assert "artifact" not in repaired_risk


def test_service_now_contract_remains_exactly_eight_fields() -> None:
    bucket_3 = _repair(_evidence())
    payload = format_service_now_payload(
        {
            "change_description": "Update account processing behavior.",
            "short_change_description": "Update account processing",
            "justification": "Improve processing consistency.",
            "testing_performed": "Supported tests completed.",
            "implementation_plan": "Deploy the approved change.",
            "validation_plan": "Validate the updated behavior.",
            "backout_plan": bucket_3["backout_plan"],
            "risk_impact_analysis": bucket_3["risk_impact_analysis"],
        }
    )

    assert tuple(payload.model_dump()) == SERVICE_NOW_FIELD_NAMES


def test_compliant_bucket_3_fields_are_not_rewritten_when_no_repair_is_requested() -> None:
    payload = {
        "backout_plan": str(_repair(_evidence())["backout_plan"]),
        "risk_impact_analysis": _risk_text("Possible"),
    }

    repaired, notes = repair_bucket_3_fields(
        payload,
        _evidence(),
        fields_to_repair=set(),
    )

    assert repaired == payload
    assert notes == []
