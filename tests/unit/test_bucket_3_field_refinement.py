"""Focused tests for concise, evidence-grounded Bucket 3 ServiceNow fields."""

from __future__ import annotations

from typing import Any

from backend.app.services.formatting.servicenow_formatter import (
    SERVICE_NOW_FIELD_NAMES,
    format_service_now_payload,
)
from backend.app.services.validation.output_repair import (
    expected_backout_duration_statement,
    repair_bucket_3_fields,
)
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
    risk_signals: list[str] | None = None,
) -> dict[str, Any]:
    if activities is None:
        activities = [
            {"name": "Get Base Solution Versions", "duration_seconds": 30},
            {
                "name": "Upgrade Solution AcctShutdownAcctCompromiseASAC",
                "duration_seconds": 480,
            },
            {
                "name": "Apply Solution Upgrade AcctShutdownAcctCompromiseASAC",
                "duration_seconds": 180,
            },
            {"name": "Update environment configuration", "duration_seconds": 180},
            {"name": "Validate application health", "duration_seconds": 240},
        ]
    return {
        "bucket_3": {
            "service_context": {"repository_name": repository_name},
            "uat_deployment": {
                "stage_name": "UAT",
                "selected_environment": "UAT" if duration_seconds is not None else None,
                "activities": activities,
                "total_deployment_duration_seconds": duration_seconds,
            },
            "backout_time_derivation": {
                "calculation_method": "lower_environment_stage_duration",
                "environment_priority": ["UAT", "QA", "TEST", "INTG", "SIT", "DEV"],
                "selected_environment": "UAT" if duration_seconds is not None else None,
                "selected_stage_name": "Deploy to UAT" if duration_seconds is not None else None,
                "stage_start_time": "2026-07-10T14:10:00Z"
                if duration_seconds is not None
                else None,
                "stage_finish_time": "2026-07-10T14:25:00Z"
                if duration_seconds is not None
                else None,
                "source_duration_seconds": duration_seconds,
                "rounding_rule": "round_up_to_nearest_5_minutes",
                "final_estimate_minutes": 15 if duration_seconds is not None else None,
            },
            "environment_candidates": (
                [
                    {
                        "stage_name": "Deploy to UAT",
                        "normalized_environment": "UAT",
                        "state": "completed",
                        "result": "succeeded",
                        "start_time": "2026-07-10T14:10:00Z",
                        "finish_time": "2026-07-10T14:25:00Z",
                        "duration_seconds": duration_seconds,
                        "deployment_activities": [
                            "Upgrade Solution AcctShutdownAcctCompromiseASAC",
                            "Apply Solution Upgrade AcctShutdownAcctCompromiseASAC",
                        ],
                        "selected": True,
                    }
                ]
                if duration_seconds is not None
                else []
            ),
            "resiliency_evidence": resiliency or {},
            "planned_impact_evidence": planned_impact or [],
            "high_risk_evidence": high_risk or [],
            "application_candidates": (
                ["Contact Center ASAC application"]
                if application_candidates is None
                else application_candidates
            ),
            "application_resolution": {
                "selected_application": "contact-center-asac",
                "display_name": "Contact Center ASAC application",
                "selection_reason": "Repository and deployment evidence matched.",
                "candidate_scores": [
                    {
                        "candidate": "contact-center-asac",
                        "score": 100,
                        "sources": ["repository", "pipeline", "uat_deployment"],
                    }
                ],
            },
            "rollback_indicators": ["UAT deployment activities"],
            "risk_flags": risk_flags or {},
            "risk_signals": risk_signals or [],
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
    if likelihood == "Improbable":
        risk_sentence = (
            "Unplanned impact is considered improbable; if an unexpected deployment issue "
            "occurs, there may be temporary functional degradation, and the previous application "
            "state can be restored using the documented backout steps."
        )
    else:
        risk_sentence = (
            f"There is a {likelihood.lower()} risk of temporary functional degradation if an "
            "unexpected deployment issue occurs; the previous application state can be restored "
            "using the documented backout steps."
        )
    return (
        "No planned service outage is expected for the Contact Center ASAC application. "
        f"{risk_sentence}"
    )


def _labeled_risk_text(likelihood: str = "Possible") -> str:
    return (
        "Planned impact: No planned service outage is identified.\n"
        "Impacted application: Contact Center ASAC application.\n"
        f"Likelihood of unplanned impact: {likelihood}.\n"
        "Potential impact: Users may experience temporary issues with account-closure processing.\n"
        "Mitigation: The previous application state can be restored."
    )


def _assert_narrative_risk_format(risk: str) -> None:
    forbidden = (
        "Planned impact:",
        "Impacted application:",
        "Likelihood of unplanned impact:",
        "Potential impact:",
        "Mitigation:",
    )
    assert 40 <= len(risk.split()) <= 110
    assert not any(label in risk for label in forbidden)
    assert "\n" not in risk
    assert r"\n" not in risk
    assert not risk.lstrip().startswith(("1.", "2.", "3.", "4.", "-", "*"))


def test_labeled_risk_input_is_repaired_to_one_natural_paragraph() -> None:
    evidence = _evidence(
        risk_signals=["Account-closure processing may be temporarily disrupted."]
    )
    labeled = _labeled_risk_text()

    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(evidence)["backout_plan"]),
            "risk_impact_analysis": labeled,
        },
        evidence,
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {"backout_plan": str(_repair(evidence)["backout_plan"]), "risk_impact_analysis": labeled},
        evidence,
        fields_to_repair={"risk_impact_analysis"},
    )

    codes = {issue.code for issue in issues}
    assert "RISK_IMPACT_LABELED_FORMAT" in codes
    assert "RISK_IMPACT_LIST_FORMAT" in codes
    risk = str(repaired["risk_impact_analysis"])
    _assert_narrative_risk_format(risk)
    assert "account-closure processing" in risk
    assert risk.count("Contact Center ASAC application") == 1
    assert "possible risk" in risk


def test_risk_list_and_literal_newline_escape_are_flagged_and_removed() -> None:
    formatted_as_list = (
        "1. No planned service outage is expected for the Contact Center ASAC application."
        r"\n"
        "2. There is a possible risk of temporary functional degradation."
    )

    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": formatted_as_list,
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": formatted_as_list,
        },
        _evidence(),
        fields_to_repair={"risk_impact_analysis"},
    )

    codes = {issue.code for issue in issues}
    assert "RISK_IMPACT_LIST_FORMAT" in codes
    assert "RISK_IMPACT_NEWLINE_ESCAPE" in codes
    _assert_narrative_risk_format(str(repaired["risk_impact_analysis"]))


def test_formatting_repair_preserves_supported_likelihood_and_selected_application() -> None:
    evidence = _evidence(high_risk=["Known recurring deployment failures affected this change."])

    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(evidence)["backout_plan"]),
            "risk_impact_analysis": _labeled_risk_text("Possible"),
        },
        evidence,
        fields_to_repair={"risk_impact_analysis"},
    )

    risk = str(repaired["risk_impact_analysis"])
    assert "possible risk" in risk
    assert "probable risk" not in risk
    assert risk.count("Contact Center ASAC application") == 1


def test_risk_repair_replaces_repeated_backout_steps_with_brief_mitigation() -> None:
    repeated_backout = (
        _labeled_risk_text()
        + "\n1. Stop or pause the production deployment."
        + "\n2. Redeploy the previously validated solution."
        + "\nEstimated backout time: approximately 15 minutes."
    )

    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": repeated_backout,
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": repeated_backout,
        },
        _evidence(),
        fields_to_repair={"risk_impact_analysis"},
    )

    assert any(issue.code == "RISK_IMPACT_BACKOUT_PLAN_REPETITION" for issue in issues)
    risk = str(repaired["risk_impact_analysis"])
    _assert_narrative_risk_format(risk)
    assert "Estimated backout time" not in risk
    assert "Stop or pause" not in risk


def test_backout_uses_uat_solution_and_configuration_reverse_steps() -> None:
    backout = str(_repair(_evidence())["backout_plan"])

    assert "Apply the prior solution version and complete the solution rollback" in backout
    assert backout.count("complete the solution rollback") == 1
    assert "Restore the previous configuration settings" in backout
    assert "Validate that the Contact Center ASAC application" in backout
    assert "Get Base Solution Versions" not in backout
    assert "pipeline" not in backout.lower()
    assert "build" not in backout.lower()
    assert "artifact" not in backout.lower()


def test_backout_rounds_observed_uat_duration_to_practical_estimate() -> None:
    backout = str(_repair(_evidence(duration_seconds=900))["backout_plan"])

    assert "Estimated backout time: approximately 15 minutes." in backout


def test_backout_without_lower_environment_timing_uses_unavailable_fallback() -> None:
    backout = str(_repair(_evidence(duration_seconds=None))["backout_plan"])

    assert "Estimated backout time: Not available from the pipeline evidence." in backout
    assert "confirm" not in backout.lower()
    assert "approximately 20 minutes" not in backout


def test_missing_lower_environment_stage_timing_is_flagged() -> None:
    evidence = _evidence(duration_seconds=None)
    evidence["bucket_3"]["warnings"] = [
        "BACKOUT_DURATION_LOWER_ENVIRONMENT_NOT_FOUND",
        "BACKOUT_DURATION_STAGE_TIMING_MISSING",
    ]
    backout = str(_repair(evidence)["backout_plan"])

    issues = validate_bucket_3_fields(
        {"backout_plan": backout, "risk_impact_analysis": _risk_text("Possible")},
        evidence,
        "bucket_3",
    )

    codes = {issue.code for issue in issues}
    assert "BACKOUT_DURATION_LOWER_ENVIRONMENT_NOT_FOUND" in codes
    assert "BACKOUT_DURATION_STAGE_TIMING_MISSING" in codes
    assert "BACKOUT_PLAN_DELIVERY_METADATA_LEAKAGE" not in codes


def test_backout_duration_rounds_up_to_five_minute_intervals() -> None:
    cases = {
        60: "approximately 5 minutes",
        301: "approximately 10 minutes",
        601: "approximately 15 minutes",
        901: "approximately 20 minutes",
        3600: "approximately 1 hour",
        3661: "approximately 1 hour 5 minutes",
    }
    for duration, expected in cases.items():
        evidence = {
            "bucket_3": {
                "uat_deployment": {"total_deployment_duration_seconds": duration}
            }
        }
        assert expected in expected_backout_duration_statement(evidence)


def test_task_level_duration_is_flagged_and_repaired_to_stage_estimate_only() -> None:
    evidence = _evidence()
    evidence["bucket_3"]["backout_time_derivation"]["calculation_method"] = (
        "sum_task_activity_durations"
    )
    generated = (
        "1. Stop the deployment.\n"
        "2. Restore the prior solution.\n"
        "3. Validate the application.\n\n"
        "Estimated backout time: approximately 5 minutes."
    )

    issues = validate_bucket_3_fields(
        {"backout_plan": generated, "risk_impact_analysis": _risk_text("Possible")},
        evidence,
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {"backout_plan": generated, "risk_impact_analysis": _risk_text("Possible")},
        evidence,
        fields_to_repair={"backout_plan"},
    )

    codes = {issue.code for issue in issues}
    assert "BACKOUT_DURATION_TASK_LEVEL_CALCULATION_USED" in codes
    assert "BACKOUT_DURATION_WRONG_STAGE_TYPE" in codes
    assert str(repaired["backout_plan"]).startswith("1. Stop the deployment.")
    assert "Estimated backout time: approximately 15 minutes." in str(
        repaired["backout_plan"]
    )


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

    _assert_narrative_risk_format(risk)
    assert risk.startswith(
        "No planned service outage is expected for the Contact Center ASAC application."
    )


def test_risk_without_backout_evidence_remains_within_narrative_length() -> None:
    evidence = _evidence(activities=[])
    evidence["bucket_3"]["rollback_indicators"] = []

    risk = str(_repair(evidence)["risk_impact_analysis"])

    _assert_narrative_risk_format(risk)
    assert "documented backout steps" not in risk


def test_explicit_outage_evidence_is_preserved_without_invention() -> None:
    supported = "Contact Center ASAC application will be unavailable for approximately 15 minutes."
    risk = str(_repair(_evidence(planned_impact=[supported]))["risk_impact_analysis"])

    _assert_narrative_risk_format(risk)
    assert risk.startswith(supported)
    assert "15 minutes" in risk
    assert "possible risk" in risk


def test_unsupported_planned_outage_is_flagged_and_repaired_to_no_identified_outage() -> None:
    unsupported = _risk_text("Possible").replace(
        "No planned service outage is expected for the Contact Center ASAC application",
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
    assert str(repaired["risk_impact_analysis"]).startswith(
        "No planned service outage is expected for the Contact Center ASAC application."
    )


def test_possible_is_default_without_resiliency_or_high_risk_evidence() -> None:
    risk = str(_repair(_evidence())["risk_impact_analysis"])

    assert "There is a possible risk" in risk


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

    _assert_narrative_risk_format(risk)
    assert "Unplanned impact is considered improbable" in risk


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
    assert "There is a possible risk" in str(repaired["risk_impact_analysis"])


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
    assert "There is a possible risk" in str(repaired["risk_impact_analysis"])


def test_explicit_recurring_failure_evidence_allows_probable() -> None:
    risk = str(
        _repair(
            _evidence(
                high_risk=["Known recurring deployment failures affected this application."]
            )
        )["risk_impact_analysis"]
    )

    assert "There is a probable risk" in risk


def test_repository_name_becomes_business_readable_application_name() -> None:
    risk = str(
        _repair(
            _evidence(
                application_candidates=[],
                repository_name="contact-center-asac",
            )
        )["risk_impact_analysis"]
    )

    assert risk.count("Contact Center ASAC application") == 1


def test_ambiguous_application_and_confirmation_language_are_flagged_and_repaired() -> None:
    ambiguous = _risk_text("Possible").replace(
        "Contact Center ASAC application",
        "Bill Pay Service, Enable service, or contact-center-asac (to be confirmed)",
    )

    issues = validate_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": ambiguous,
        },
        _evidence(),
        "bucket_3",
    )
    repaired, _ = repair_bucket_3_fields(
        {
            "backout_plan": str(_repair(_evidence())["backout_plan"]),
            "risk_impact_analysis": ambiguous,
        },
        _evidence(),
        fields_to_repair={"risk_impact_analysis"},
    )

    codes = {issue.code for issue in issues}
    assert "IMPACT_APPLICATION_CONFIRMATION_LANGUAGE" in codes
    assert "IMPACT_APPLICATION_MULTIPLE_ALTERNATIVES" in codes
    assert "IMPACT_APPLICATION_AMBIGUOUS" in codes
    assert "IMPACT_APPLICATION_WEAK_EVIDENCE_SELECTED" in codes
    repaired_risk = str(repaired["risk_impact_analysis"])
    assert repaired_risk.count("Contact Center ASAC application") == 1
    assert "to be confirmed" not in repaired_risk.lower()
    assert "Bill Pay" not in repaired_risk


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
