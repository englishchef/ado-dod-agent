"""Deterministic validators for generated DoD ServiceNow payloads."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import ValidationError

from backend.app.models.llm_outputs import CombinedLlmOutputs
from backend.app.models.validated_outputs import (
    PLACEHOLDER_VALUES,
    BucketValidationResult,
    ServiceNowPayload,
    ValidationIssue,
)
from backend.app.services.evidence.bucket_3_selection import (
    display_application_name,
    normalize_application_candidate,
    normalize_environment_name,
)
from backend.app.services.validation.output_repair import (
    bucket_3_claim_evidence_text,
    detect_backout_delivery_metadata_leakage,
    detect_delivery_detail_leakage,
    expected_backout_duration_statement,
    has_explicit_planned_impact_evidence,
    has_high_risk_evidence,
    has_resiliency_evidence,
    longest_contiguous_word_overlap,
    normalized_words,
    sequence_similarity,
)

Severity = Literal["info", "warning", "error"]

BUCKET_FIELDS = {
    "bucket_1": ("change_description", "short_change_description", "justification"),
    "bucket_2": ("testing_performed", "implementation_plan", "validation_plan"),
    "bucket_3": ("backout_plan", "risk_impact_analysis"),
}

_RAW_REFERENCE_LEAKAGE_RE = re.compile(
    r"(\[(?:raw|canonical|evidence)\.[^\]]+\]|"
    r"\b(?:raw|canonical|evidence)\.[A-Za-z0-9_.-]+(?:\[[0-9]+\])*|"
    r"\bsource_ref(?:_map)?\b)",
    re.IGNORECASE,
)
_CHANGE_ENUMERATION_RE = re.compile(
    r"\b(?:add|adds|change|changes|correct|corrects|enhance|enhances|fix|fixes|"
    r"implement|implements|introduce|introduces|modify|modifies|resolve|resolves|"
    r"support|supports|update|updates)\b",
    re.IGNORECASE,
)
_RATIONALE_RE = re.compile(
    r"\b(?:because|benefit|compliance|correctness|efficiency|ensure|necessary|prevent|"
    r"reduce|reliability|required|risk|supportability)\b|user experience|"
    r"operational consistency",
    re.IGNORECASE,
)
_BACKOUT_STEP_RE = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*])\s+\S+")
_BACKOUT_DURATION_RE = re.compile(r"(?im)^\s*Estimated backout time\s*:\s*.+$")
_LIKELIHOOD_RE = re.compile(
    r"\b(probable|possible|improbable)\b",
    re.IGNORECASE,
)
_ALLOWED_LIKELIHOODS = {"probable", "possible", "improbable"}
_RISK_IMPACT_LABEL_RE = re.compile(
    r"\b(?:Planned impact|Impacted (?:application|service)|"
    r"Likelihood of unplanned impact|Potential impact|Mitigation)\s*:",
    re.IGNORECASE,
)
_RISK_IMPACT_LIST_RE = re.compile(r"(?m)^\s*(?:[-*\u2022]|\d+[.)])\s+\S+")
_RISK_IMPACT_BACKOUT_REPETITION_RE = re.compile(
    r"Estimated backout time\s*:|Stop or pause the production deployment|"
    r"Redeploy the previously validated|Apply the prior solution state|"
    r"Validate that the .+? operate normally",
    re.IGNORECASE,
)
_RISK_IMPACT_NEGATIVE_PLANNED_RE = re.compile(
    r"\b(?:no|without)\s+(?:planned\s+)?(?:service\s+)?"
    r"(?:outage|downtime|impact|degradation|disruption)\b"
    r"|\b(?:no\s+)?planned\s+(?:service\s+)?(?:outage|impact)\s+is\s+"
    r"(?:expected|identified|anticipated)\b",
    re.IGNORECASE,
)
_RISK_IMPACT_POSITIVE_PLANNED_RE = re.compile(
    r"\bwill be unavailable\b|\bscheduled\s+(?:service\s+)?(?:outage|downtime)\b|"
    r"\bplanned\s+(?:service\s+)?(?:outage|downtime|impact|degradation|disruption)\b|"
    r"\bintermittent access\b",
    re.IGNORECASE,
)
_RISK_IMPACT_APPLICATION_ALTERNATIVES_RE = re.compile(
    r"\b(?:application|service)\b[^.!?]{0,80}\bor\b[^.!?]{0,80}"
    r"\b(?:application|service)\b|"
    r"\b(?:application|service)\b[^.!?]{0,80},\s*or\b",
    re.IGNORECASE,
)
_UNSUPPORTED_RISK_CLAIMS = (
    "worst-case scenario",
    "data loss",
    "database corruption",
    "regional failover",
    "complete service failure",
    "authentication failure",
    "secret retrieval failure",
    "operational disruption to all business processes",
    "production instability",
)
_RISK_DELIVERY_METADATA_RE = re.compile(
    r"\b(?:artifact|branch|build(?:\s+(?:id|number))?|commit|pipeline|version\s+\d)\b|"
    r"\bAzure\s+DevOps\b|\bCI\s*/\s*CD\b",
    re.IGNORECASE,
)
_CONFIRMATION_LANGUAGE_RE = re.compile(
    r"\b(?:to be confirmed|confirmation required|must be confirmed|"
    r"implementation team (?:should|must) confirm|submitter must confirm|"
    r"requires confirmation|application or service associated with this deployment|"
    r"one of the following applications)\b",
    re.IGNORECASE,
)
def validate_llm_outputs(
    llm_outputs: CombinedLlmOutputs | dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
) -> list[BucketValidationResult]:
    """Validate each generated bucket output without repairing or regenerating content."""

    payload = _as_dict(llm_outputs)
    evidence = evidence_bundle or {}
    results: list[BucketValidationResult] = []
    for bucket_name, required_fields in BUCKET_FIELDS.items():
        bucket_payload = payload.get(bucket_name)
        issues: list[ValidationIssue] = []
        if not isinstance(bucket_payload, dict):
            issues.append(
                _issue(
                    "error",
                    "missing_bucket",
                    "Required bucket output is missing.",
                    None,
                    bucket_name,
                )
            )
            results.append(
                BucketValidationResult(bucket_name=bucket_name, is_valid=False, issues=issues)
            )
            continue

        for field in required_fields:
            _validate_text_field(bucket_payload.get(field), field, bucket_name, issues)

        evidence_used = bucket_payload.get("evidence_used")
        if not isinstance(evidence_used, list) or len(evidence_used) == 0:
            issues.append(
                _issue(
                    "warning",
                    "missing_evidence_used",
                    "Bucket output does not include evidence_used references.",
                    "evidence_used",
                    bucket_name,
                )
            )

        issues.extend(_unsupported_claim_issues(bucket_name, bucket_payload, evidence))
        if bucket_name == "bucket_1":
            issues.extend(validate_change_intent_field_separation(bucket_payload, bucket_name))
        if bucket_name == "bucket_3":
            issues.extend(validate_bucket_3_fields(bucket_payload, evidence, bucket_name))
        issues.extend(_missing_context_issues(bucket_name, evidence))
        results.append(
            BucketValidationResult(
                bucket_name=bucket_name,
                is_valid=not any(issue.severity == "error" for issue in issues),
                issues=issues,
            )
        )
    return results


def detect_raw_reference_leakage(text: str) -> bool:
    """Return whether text contains raw/internal evidence references."""

    return bool(_RAW_REFERENCE_LEAKAGE_RE.search(text))


def validate_no_raw_reference_leakage(
    payload: ServiceNowPayload | dict[str, Any],
) -> list[ValidationIssue]:
    """Validate that final ServiceNow fields do not expose internal evidence refs."""

    payload_dict = payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
    issues: list[ValidationIssue] = []
    for field, value in payload_dict.items():
        if isinstance(value, str) and detect_raw_reference_leakage(value):
            issues.append(
                _issue(
                    "error",
                    "RAW_REFERENCE_LEAKAGE",
                    "Final ServiceNow field contains internal evidence reference.",
                    field,
                    None,
                )
            )
    return issues


def validate_change_intent_field_separation(
    payload: ServiceNowPayload | dict[str, Any],
    bucket: str | None = None,
) -> list[ValidationIssue]:
    """Validate that description and justification serve distinct field purposes."""

    payload_dict = payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
    change_description = payload_dict.get("change_description")
    justification = payload_dict.get("justification")
    issues: list[ValidationIssue] = []

    if isinstance(change_description, str) and detect_delivery_detail_leakage(
        change_description
    ):
        issues.append(
            _issue(
                "warning",
                "CHANGE_DESCRIPTION_DELIVERY_DETAIL_LEAKAGE",
                "Change description contains build, source-control, or delivery metadata.",
                "change_description",
                bucket,
            )
        )
    if isinstance(justification, str) and detect_delivery_detail_leakage(justification):
        issues.append(
            _issue(
                "warning",
                "JUSTIFICATION_DELIVERY_DETAIL_LEAKAGE",
                "Justification contains build, source-control, or delivery metadata.",
                "justification",
                bucket,
            )
        )
    if not isinstance(change_description, str) or not isinstance(justification, str):
        return issues

    description_words = normalized_words(change_description)
    justification_words = normalized_words(justification)
    shorter_word_count = min(len(description_words), len(justification_words))
    similarity = sequence_similarity(change_description, justification)
    longest_overlap = longest_contiguous_word_overlap(change_description, justification)
    if shorter_word_count >= 18 and similarity >= 0.88:
        issues.append(
            _issue(
                "warning",
                "JUSTIFICATION_REPETITIVE",
                "Justification is nearly identical to change description.",
                "justification",
                bucket,
            )
        )

    overlap_reasons: list[str] = []
    if longest_overlap >= 15:
        overlap_reasons.append("copies a long contiguous phrase from change description")
    if (
        len(description_words) >= 50
        and len(justification_words) >= 90
        and len(justification_words) > len(description_words) * 1.25
    ):
        overlap_reasons.append("is substantially longer than change description")
    change_terms = len(_CHANGE_ENUMERATION_RE.findall(justification))
    rationale_terms = len(_RATIONALE_RE.findall(justification))
    if change_terms >= 4 and rationale_terms <= 1:
        overlap_reasons.append("primarily enumerates changes instead of explaining rationale")
    if overlap_reasons:
        issues.append(
            _issue(
                "warning",
                "FIELD_PURPOSE_OVERLAP",
                "Justification " + "; ".join(overlap_reasons) + ".",
                "justification",
                bucket,
            )
        )
    return issues


def validate_bucket_3_fields(
    payload: ServiceNowPayload | dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
    bucket: str | None = None,
) -> list[ValidationIssue]:
    """Validate concise, evidence-grounded backout and risk field intent."""

    payload_dict = payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
    evidence = evidence_bundle or {}
    issues: list[ValidationIssue] = []
    backout = payload_dict.get("backout_plan")
    if isinstance(backout, str) and backout.strip():
        if _CONFIRMATION_LANGUAGE_RE.search(backout):
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_PLAN_CONFIRMATION_LANGUAGE",
                    "Backout plan must use deterministic evidence wording without "
                    "confirmation language.",
                    "backout_plan",
                    bucket,
                )
            )
        if detect_backout_delivery_metadata_leakage(backout):
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_PLAN_DELIVERY_METADATA_LEAKAGE",
                    "Backout plan contains build, version, branch, pipeline, artifact, or "
                    "delivery metadata.",
                    "backout_plan",
                    bucket,
                )
            )
        if len(_BACKOUT_STEP_RE.findall(backout)) < 2:
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_PLAN_MISSING_STEPS",
                    "Backout plan must contain ordered or clearly separated operational steps.",
                    "backout_plan",
                    bucket,
                )
            )
        if len(normalized_words(backout)) > 120:
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_PLAN_TOO_VERBOSE",
                    "Backout plan contains explanatory narrative beyond the rollback actions.",
                    "backout_plan",
                    bucket,
                )
            )
        duration_match = _BACKOUT_DURATION_RE.search(backout)
        if duration_match is None:
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_PLAN_MISSING_DURATION",
                    "Backout plan must include an estimated backout time.",
                    "backout_plan",
                    bucket,
                )
            )
        else:
            expected_duration = expected_backout_duration_statement(evidence)
            if duration_match.group(0).strip().casefold() != expected_duration.casefold():
                issues.append(
                    _issue(
                        "warning",
                        "BACKOUT_DURATION_UNSUPPORTED",
                        "Backout duration does not match the rounded selected lower-environment "
                        "deployment-stage timing evidence or unavailable-evidence fallback.",
                        "backout_plan",
                        bucket,
                    )
                )
        issues.extend(_backout_derivation_issues(evidence, bucket))

    risk = payload_dict.get("risk_impact_analysis")
    if not isinstance(risk, str) or not risk.strip():
        return issues
    risk_sentences = _risk_impact_sentences(risk)
    if len(normalized_words(risk)) > 110 or len(risk_sentences) > 2:
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_TOO_VERBOSE",
                "Risk and impact analysis should remain within approximately 40-110 words and "
                "no more than two sentences.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if _RISK_IMPACT_LABEL_RE.search(risk):
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_LABELED_FORMAT",
                "Risk and impact analysis must use natural sentences without field labels.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if "\n" in risk or "\r" in risk or _RISK_IMPACT_LIST_RE.search(risk):
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_LIST_FORMAT",
                "Risk and impact analysis must be one paragraph without bullets or numbering.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if r"\n" in risk:
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_NEWLINE_ESCAPE",
                "Risk and impact analysis contains a raw newline escape sequence.",
                "risk_impact_analysis",
                bucket,
            )
        )
    backout_repetition_markers = _RISK_IMPACT_BACKOUT_REPETITION_RE.findall(risk)
    if (
        re.search(r"Estimated backout time\s*:", risk, re.IGNORECASE)
        or len(_BACKOUT_STEP_RE.findall(risk)) >= 2
        or len(backout_repetition_markers) >= 2
    ):
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_BACKOUT_PLAN_REPETITION",
                "Risk and impact analysis must not repeat the detailed backout plan.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if _CONFIRMATION_LANGUAGE_RE.search(risk):
        issues.extend(
            [
                _issue(
                    "warning",
                    "IMPACT_APPLICATION_CONFIRMATION_LANGUAGE",
                    "Impacted application must not contain confirmation language.",
                    "risk_impact_analysis",
                    bucket,
                ),
                _issue(
                    "warning",
                    "IMPACT_APPLICATION_AMBIGUOUS",
                    "Impacted application must resolve to one concrete evidence-backed value.",
                    "risk_impact_analysis",
                    bucket,
                ),
            ]
        )
    first_sentence = risk_sentences[0] if risk_sentences else risk
    negative_planned_impact = _RISK_IMPACT_NEGATIVE_PLANNED_RE.search(first_sentence)
    positive_planned_impact = _RISK_IMPACT_POSITIVE_PLANNED_RE.search(first_sentence)
    if negative_planned_impact is None and positive_planned_impact is None:
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_MISSING_PLANNED_IMPACT",
                "Risk and impact analysis must state the evidence-supported planned impact.",
                "risk_impact_analysis",
                bucket,
            )
        )
    expected_application = _expected_application_display(evidence)
    expected_application_count = (
        risk.casefold().count(expected_application.casefold()) if expected_application else 0
    )
    has_application_reference = bool(
        re.search(
            r"\bfor\s+(?:the\s+)?[^.!?]{1,80}\b(?:application|service)\b|"
            r"\b(?:application|service)\s+(?:will|may|is|can)\b",
            risk,
            re.IGNORECASE,
        )
    )
    if (expected_application and expected_application_count == 0) or (
        not expected_application and not has_application_reference
    ):
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_MISSING_APPLICATION",
                "Risk and impact analysis must identify the impacted application or service.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if expected_application and expected_application_count == 0:
        issues.append(
            _issue(
                "warning",
                "IMPACT_APPLICATION_WEAK_EVIDENCE_SELECTED",
                "Impacted application does not match the strongest deterministic candidate.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if expected_application_count > 1 or _RISK_IMPACT_APPLICATION_ALTERNATIVES_RE.search(risk):
        issues.extend(
            [
                _issue(
                    "warning",
                    "IMPACT_APPLICATION_MULTIPLE_ALTERNATIVES",
                    "Risk and impact analysis must contain exactly one impacted application.",
                    "risk_impact_analysis",
                    bucket,
                ),
                _issue(
                    "warning",
                    "IMPACT_APPLICATION_AMBIGUOUS",
                    "Impacted application must resolve to exactly one candidate.",
                    "risk_impact_analysis",
                    bucket,
                ),
            ]
        )
    likelihood_match = _LIKELIHOOD_RE.search(risk)
    if likelihood_match is None:
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_MISSING_LIKELIHOOD",
                "Risk and impact analysis must classify likelihood as Probable, Possible, or "
                "Improbable.",
                "risk_impact_analysis",
                bucket,
            )
        )
    else:
        likelihood = likelihood_match.group(1).lower()
        if likelihood not in _ALLOWED_LIKELIHOODS:
            issues.append(
                _issue(
                    "warning",
                    "RISK_LIKELIHOOD_UNSUPPORTED",
                    "Likelihood must be Probable, Possible, or Improbable.",
                    "risk_impact_analysis",
                    bucket,
                )
            )
        elif likelihood == "improbable" and not has_resiliency_evidence(evidence):
            issues.append(
                _issue(
                    "warning",
                    "IMPROBABLE_WITHOUT_RESILIENCY_EVIDENCE",
                    "Improbable requires explicit resiliency or traffic-protection evidence.",
                    "risk_impact_analysis",
                    bucket,
                )
            )
        elif likelihood == "probable" and not has_high_risk_evidence(evidence):
            issues.append(
                _issue(
                    "warning",
                    "PROBABLE_WITHOUT_HIGH_RISK_EVIDENCE",
                    "Probable requires explicit recurring-failure, incident, instability, "
                    "failed-validation, or high-risk evidence.",
                    "risk_impact_analysis",
                    bucket,
                )
            )
    if re.search(r"\b\d+(?:\.\d+)?\s*%", risk):
        issues.append(
            _issue(
                "warning",
                "RISK_LIKELIHOOD_UNSUPPORTED",
                "Numeric likelihood percentages are not supported by the ServiceNow field "
                "contract.",
                "risk_impact_analysis",
                bucket,
            )
        )
    if not re.search(
        r"\b(?:risk of|may|could|temporar(?:y|ily)|potential impact|"
        r"if (?:an )?(?:unexpected|implementation|deployment))\b",
        risk,
        re.IGNORECASE,
    ):
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_MISSING_POTENTIAL_IMPACT",
                "Risk and impact analysis must describe one realistic potential impact.",
                "risk_impact_analysis",
                bucket,
            )
        )
    evidence_text = bucket_3_claim_evidence_text(evidence).lower()
    unsupported_claims = [
        claim
        for claim in _UNSUPPORTED_RISK_CLAIMS
        if claim in risk.lower() and claim not in evidence_text
    ]
    if _RISK_DELIVERY_METADATA_RE.search(risk):
        unsupported_claims.append("delivery metadata")
    if (
        positive_planned_impact
        and not negative_planned_impact
        and not has_explicit_planned_impact_evidence(evidence)
    ):
        unsupported_claims.append("planned outage or degradation")
    if unsupported_claims:
        unsupported_claims = list(dict.fromkeys(unsupported_claims))
        issues.append(
            _issue(
                "warning",
                "RISK_IMPACT_SPECULATIVE",
                "Risk and impact analysis contains unsupported speculative impact claims: "
                + ", ".join(unsupported_claims)
                + ".",
                "risk_impact_analysis",
                bucket,
            )
        )
    return issues


def _risk_impact_sentences(value: str) -> list[str]:
    normalized = re.sub(r"\\n|[\r\n]+", " ", value.strip())
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def _backout_derivation_issues(
    evidence_bundle: dict[str, Any],
    bucket: str | None,
) -> list[ValidationIssue]:
    evidence = _bucket(evidence_bundle, "bucket_3")
    derivation = evidence.get("backout_time_derivation")
    if not isinstance(derivation, dict):
        return []
    issues: list[ValidationIssue] = []
    method = str(derivation.get("calculation_method") or "")
    if method and method != "lower_environment_stage_duration":
        issues.append(
            _issue(
                "warning",
                "BACKOUT_DURATION_WRONG_STAGE_TYPE",
                "Backout duration must be calculated from a lower-environment deployment stage.",
                "backout_plan",
                bucket,
            )
        )
    if re.search(r"(?:task|activity|sum)", method, re.IGNORECASE):
        issues.append(
            _issue(
                "warning",
                "BACKOUT_DURATION_TASK_LEVEL_CALCULATION_USED",
                "Individual activity durations cannot be used for backout-time estimation.",
                "backout_plan",
                bucket,
            )
        )

    selected_environment = str(derivation.get("selected_environment") or "")
    selected_stage_name = str(derivation.get("selected_stage_name") or "")
    if (
        selected_environment == "PRODUCTION"
        or normalize_environment_name(selected_stage_name) == "PRODUCTION"
    ):
        issues.append(
            _issue(
                "warning",
                "BACKOUT_DURATION_PRODUCTION_STAGE_SELECTED",
                "Production stages cannot be used for backout-time estimation.",
                "backout_plan",
                bucket,
            )
        )
    if not selected_environment:
        issues.append(
            _issue(
                "warning",
                "BACKOUT_DURATION_LOWER_ENVIRONMENT_NOT_FOUND",
                "No valid lower-environment deployment stage was available.",
                "backout_plan",
                bucket,
            )
        )
        warnings = evidence.get("warnings")
        if isinstance(warnings, list) and (
            "BACKOUT_DURATION_STAGE_TIMING_MISSING" in warnings
        ):
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_DURATION_STAGE_TIMING_MISSING",
                    "Lower-environment deployment-stage start or finish timing is missing.",
                    "backout_plan",
                    bucket,
                )
            )
        return issues
    if not derivation.get("stage_start_time") or not derivation.get("stage_finish_time"):
        issues.append(
            _issue(
                "warning",
                "BACKOUT_DURATION_STAGE_TIMING_MISSING",
                "Selected lower-environment deployment stage is missing start or finish timing.",
                "backout_plan",
                bucket,
            )
        )

    candidates = evidence.get("environment_candidates")
    if isinstance(candidates, list):
        selected_candidate: dict[str, Any] | None = None
        uat_available = False
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("selected") is True:
                selected_candidate = candidate
            if (
                candidate.get("normalized_environment") == "UAT"
                and candidate.get("duration_seconds")
                and candidate.get("deployment_activities")
                and _successful_candidate(candidate)
            ):
                uat_available = True
        if selected_candidate is not None and not selected_candidate.get(
            "deployment_activities"
        ):
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_DURATION_WRONG_STAGE_TYPE",
                    "Selected stage does not contain a valid deployment activity.",
                    "backout_plan",
                    bucket,
                )
            )
        if selected_environment != "UAT" and uat_available:
            issues.append(
                _issue(
                    "warning",
                    "BACKOUT_DURATION_WRONG_STAGE_TYPE",
                    "A valid UAT deployment stage exists and must take priority.",
                    "backout_plan",
                    bucket,
                )
            )
    return issues


def _successful_candidate(candidate: dict[str, Any]) -> bool:
    result = re.sub(r"[^a-z]", "", str(candidate.get("result") or "").lower())
    state = re.sub(r"[^a-z]", "", str(candidate.get("state") or "").lower())
    if result in {"failed", "canceled", "cancelled", "skipped", "abandoned"}:
        return False
    if state in {"canceled", "cancelled", "skipped", "notstarted", "pending"}:
        return False
    return (
        result in {"succeeded", "succeededwithissues", "partiallysucceeded"}
        or state in {"completed", "inprogress"}
        or bool(candidate.get("finish_time"))
    )


def _expected_application_display(evidence_bundle: dict[str, Any]) -> str | None:
    bucket = _bucket(evidence_bundle, "bucket_3")
    resolution = bucket.get("application_resolution")
    if not isinstance(resolution, dict):
        return None
    candidate_scores = resolution.get("candidate_scores")
    if isinstance(candidate_scores, list):
        ranked = [
            item
            for item in candidate_scores
            if isinstance(item, dict)
            and isinstance(item.get("candidate"), str)
            and isinstance(item.get("score"), int | float)
        ]
        ranked.sort(
            key=lambda item: (
                -float(item["score"]),
                normalize_application_candidate(str(item["candidate"])),
            )
        )
        if ranked:
            return display_application_name(str(ranked[0]["candidate"]))
    display_name = resolution.get("display_name")
    return display_name if isinstance(display_name, str) and display_name.strip() else None


def validate_service_now_payload(
    payload: ServiceNowPayload | dict[str, Any],
    evidence_bundle: dict[str, Any] | None = None,
) -> list[ValidationIssue]:
    """Validate the final flat ServiceNow payload."""

    evidence = evidence_bundle or {}
    issues: list[ValidationIssue] = []
    payload_model: ServiceNowPayload | None = None
    try:
        payload_model = ServiceNowPayload.model_validate(
            payload.model_dump() if isinstance(payload, ServiceNowPayload) else payload
        )
    except ValidationError as exc:
        for error in exc.errors():
            field = str(error.get("loc", ["unknown"])[0])
            issues.append(
                _issue("error", "invalid_service_now_field", str(error["msg"]), field, None)
            )

    payload_dict = (
        payload_model.model_dump()
        if payload_model is not None
        else payload.model_dump()
        if isinstance(payload, ServiceNowPayload)
        else payload
    )
    issues.extend(validate_no_raw_reference_leakage(payload_dict))
    issues.extend(validate_change_intent_field_separation(payload_dict))
    issues.extend(validate_bucket_3_fields(payload_dict, evidence))
    joined_payload = " ".join(str(value) for value in payload_dict.values())
    issues.extend(_risk_claim_issues(joined_payload, None, "risk_impact_analysis"))
    if _tests_missing(evidence):
        issues.extend(_test_claim_issues(joined_payload, None, "testing_performed"))
    if not _rollback_validation_supported(evidence):
        issues.extend(_rollback_claim_issues(joined_payload, None, "backout_plan"))
    return issues


def _as_dict(llm_outputs: CombinedLlmOutputs | dict[str, Any]) -> dict[str, Any]:
    if isinstance(llm_outputs, CombinedLlmOutputs):
        return llm_outputs.model_dump(mode="json")
    return llm_outputs


def _validate_text_field(
    value: Any,
    field: str,
    bucket: str,
    issues: list[ValidationIssue],
) -> None:
    if value is None:
        issues.append(
            _issue("error", "missing_required_field", "Required field is missing.", field, bucket)
        )
        return
    if not isinstance(value, str) or value.strip() == "":
        issues.append(
            _issue("error", "empty_required_field", "Required field is empty.", field, bucket)
        )
        return
    if value.strip().lower() in PLACEHOLDER_VALUES:
        issues.append(
            _issue("error", "placeholder_field", "Field contains placeholder text.", field, bucket)
        )


def _unsupported_claim_issues(
    bucket_name: str,
    bucket_payload: dict[str, Any],
    evidence_bundle: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field, text in bucket_payload.items():
        if not isinstance(text, str):
            continue
        if _tests_missing(evidence_bundle):
            issues.extend(_test_claim_issues(text, bucket_name, field))
        if not _rollback_validation_supported(evidence_bundle):
            issues.extend(_rollback_claim_issues(text, bucket_name, field))
        issues.extend(_risk_claim_issues(text, bucket_name, field))
    return issues


def _missing_context_issues(
    bucket_name: str,
    evidence_bundle: dict[str, Any],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if bucket_name == "bucket_1":
        bucket = _bucket(evidence_bundle, "bucket_1")
        if not bucket.get("pull_request_evidence"):
            issues.append(
                _issue(
                    "info",
                    "missing_pr_evidence",
                    "Pull request evidence is missing.",
                    None,
                    bucket_name,
                )
            )
        if not bucket.get("work_item_evidence"):
            issues.append(
                _issue(
                    "warning",
                    "missing_work_item_evidence",
                    "Work item evidence is missing.",
                    None,
                    bucket_name,
                )
            )
    if bucket_name == "bucket_2" and _tests_missing(evidence_bundle):
        issues.append(
            _issue(
                "warning",
                "missing_test_evidence",
                "Test result evidence is missing.",
                None,
                bucket_name,
            )
        )
    bucket_3 = _bucket(evidence_bundle, "bucket_3")
    if bucket_name == "bucket_3" and not bucket_3.get("artifact_evidence"):
        issues.append(
            _issue(
                "warning",
                "missing_artifact_evidence",
                "Artifact evidence is missing.",
                None,
                bucket_name,
            )
        )
    return issues


def _test_claim_issues(
    text: str,
    bucket: str | None,
    field: str | None,
) -> list[ValidationIssue]:
    phrases = (
        "tests passed",
        "all tests passed",
        "automated tests passed",
        "functional tests passed",
        "regression tests passed",
    )
    if any(phrase in text.lower() for phrase in phrases):
        return [
            _issue(
                "warning",
                "unsupported_test_claim",
                "Test pass claim is not supported by collected test evidence.",
                field,
                bucket,
            )
        ]
    return []


def _rollback_claim_issues(
    text: str,
    bucket: str | None,
    field: str | None,
) -> list[ValidationIssue]:
    phrases = ("rollback tested", "backout tested", "rollback validated")
    if any(phrase in text.lower() for phrase in phrases):
        return [
            _issue(
                "warning",
                "unsupported_rollback_claim",
                "Rollback validation claim is not supported by collected evidence.",
                field,
                bucket,
            )
        ]
    return []


def _risk_claim_issues(
    text: str,
    bucket: str | None,
    field: str | None,
) -> list[ValidationIssue]:
    phrases = ("no risk", "no impact", "zero risk")
    if any(phrase in text.lower() for phrase in phrases):
        return [
            _issue(
                "warning",
                "absolute_risk_claim",
                "Absolute no-risk/no-impact claim should be qualified by collected evidence.",
                field,
                bucket,
            )
        ]
    return []


def _tests_missing(evidence_bundle: dict[str, Any]) -> bool:
    test_evidence = _bucket(evidence_bundle, "bucket_2").get("test_evidence")
    if not isinstance(test_evidence, dict):
        return True
    missing_context = test_evidence.get("missing_test_context") or []
    total_tests = test_evidence.get("total_tests")
    return bool(missing_context) or total_tests in (None, 0)


def _rollback_validation_supported(evidence_bundle: dict[str, Any]) -> bool:
    bucket_3 = _bucket(evidence_bundle, "bucket_3")
    indicators = " ".join(
        str(item).lower() for item in bucket_3.get("rollback_indicators", [])
    )
    signals = " ".join(str(item).lower() for item in bucket_3.get("risk_signals", []))
    supported_terms = ("rollback tested", "rollback validated", "backout tested")
    return any(term in f"{indicators} {signals}" for term in supported_terms)


def _bucket(evidence_bundle: dict[str, Any], name: str) -> dict[str, Any]:
    payload = evidence_bundle.get(name)
    return payload if isinstance(payload, dict) else {}


def _issue(
    severity: Severity,
    code: str,
    message: str,
    field: str | None,
    bucket: str | None,
) -> ValidationIssue:
    return ValidationIssue(
        severity=severity,
        code=code,
        message=message,
        field=field,
        bucket=bucket,
    )
