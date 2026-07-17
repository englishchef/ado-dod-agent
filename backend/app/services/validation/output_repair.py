"""Deterministic repair helpers for generated LLM output."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from backend.app.services.llm.json_parser import JsonParseError, extract_json_object

ALIASES = {
    "risk_and_impact_analysis": "risk_impact_analysis",
    "risk_impact": "risk_impact_analysis",
    "rollback_plan": "backout_plan",
    "backout_strategy": "backout_plan",
    "test_plan": "validation_plan",
    "implementation_steps": "implementation_plan",
    "short_description": "short_change_description",
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
_DELIVERY_DETAIL_PATTERNS = (
    re.compile(r"\bbuild\s+(?:number|id)\b", re.IGNORECASE),
    re.compile(r"\bbuild\s+(?=[A-Za-z0-9._-]*\d)[A-Za-z0-9._-]+\b", re.IGNORECASE),
    re.compile(r"\bbuild\s*[#:=]\s*[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"\b(?:master|main|source|target)\s+branch\b", re.IGNORECASE),
    re.compile(r"\bbranch\s+(?:name|id)\b", re.IGNORECASE),
    re.compile(r"\bbranch\s+(?:refs/heads/)?[A-Za-z0-9._-]+[/_-][A-Za-z0-9._/-]+", re.IGNORECASE),
    re.compile(
        r"\b(?:from|on|using)\s+(?:the\s+)?[A-Za-z0-9._/-]+\s+branch\b",
        re.IGNORECASE,
    ),
    re.compile(r"\brefs/heads/[A-Za-z0-9._/-]+", re.IGNORECASE),
    re.compile(r"\b(?:source\s+)?commit(?:\s+(?:id|sha|hash))?\b", re.IGNORECASE),
    re.compile(r"\b(?:build|release|deployment)\s+artifact\b", re.IGNORECASE),
    re.compile(r"\bartifact\s+(?:name|id|version|file|package)\b", re.IGNORECASE),
    re.compile(r"\bartifact\s+[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+", re.IGNORECASE),
    re.compile(r"\brelease\s+package\b", re.IGNORECASE),
    re.compile(r"\bCI\s*/\s*CD\b|\bCICD\b", re.IGNORECASE),
    re.compile(r"\bAzure\s+DevOps\s+pipeline\b", re.IGNORECASE),
    re.compile(r"\b(?:build|release|deployment)\s+pipeline\b", re.IGNORECASE),
    re.compile(r"\bpipeline\s+(?:name|id|called|named)\b", re.IGNORECASE),
    re.compile(
        r"\b[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*[-_]"
        r"(?:ci|cd|cicd|release|deploy|deployment)\s+pipeline\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:deployed|delivered|promoted)\s+(?:through|via|by)\b", re.IGNORECASE),
    re.compile(r"\bgenerated\s+by\s+(?:the\s+)?pipeline\b", re.IGNORECASE),
    re.compile(r"\brelease\s+(?:is|was|will be)\s+built\b", re.IGNORECASE),
    re.compile(r"\bbuilt\s+and\s+deployed\s+through\b", re.IGNORECASE),
)
_TRAILING_DELIVERY_CLAUSE_PATTERNS = (
    re.compile(
        r"(?:,\s*)?(?:and|while)\s+(?:the\s+)?"
        r"(?:release|change|build|package|application|service)\s+"
        r"(?:is|was|will be)\s+(?:built|generated|deployed|delivered|promoted)\b.*$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:,\s*)?(?:and\s+)?(?:is|was|will be)\s+(?:"
        r"(?:deployed|delivered|promoted)\b|"
        r"built\s+(?:and\s+deployed|from|by|through|using)\b|"
        r"generated\s+(?:by|through|from)\b).*?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:,\s*)?(?:using|via|through|from)\s+(?:the\s+)?"
        r"(?:build|pipeline|branch|artifact|commit|CI\s*/\s*CD)\b.*$",
        re.IGNORECASE,
    ),
)
_RATIONALE_TERMS = (
    "because",
    "necessary",
    "required",
    "risk",
    "benefit",
    "reliability",
    "correctness",
    "compliance",
    "efficiency",
    "supportability",
    "user experience",
    "operational consistency",
    "reduce",
    "prevent",
    "avoid",
    "ensure",
)
_BACKOUT_DELIVERY_METADATA_PATTERNS = (
    *_DELIVERY_DETAIL_PATTERNS,
    re.compile(r"\b(?:artifact|branch|build|commit|pipeline|version)\b", re.IGNORECASE),
    re.compile(r"\bAzure\s+DevOps\b", re.IGNORECASE),
    re.compile(r"\bversion\s+(?:number\s+)?v?\d+(?:\.\d+){1,3}\b", re.IGNORECASE),
    re.compile(r"\bv?\d+\.\d+(?:\.\d+){1,2}(?:[-+][A-Za-z0-9.-]+)?\b", re.IGNORECASE),
    re.compile(r"\blast known stable build\b", re.IGNORECASE),
    re.compile(
        r"\b(?:stakeholder|implementation team)\s+"
        r"(?:coordination|communication|review)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:notify|coordinate with|communicate with)\s+(?:the\s+)?"
        r"(?:stakeholders?|support|business|implementation team)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:explicit rollback validation )?evidence\s+(?:was\s+)?"
        r"(?:not available|missing|unavailable)\b",
        re.IGNORECASE,
    ),
)
_CONFIRM_BACKOUT_DURATION = (
    "Estimated backout time: To be confirmed by the implementation team before change execution."
)
_RESILIENCY_BOOL_FIELDS = (
    "active_active",
    "rolling_deployment",
    "traffic_shift",
    "passive_instance_available",
)
_HIGH_RISK_RE = re.compile(
    r"\b(?:known\s+)?recurring\s+(?:deployment\s+)?failures?\b|"
    r"\brepeated\s+(?:historical\s+)?incidents?\b|"
    r"\bunresolved\s+critical\s+(?:defect|issue|bug)s?\b|"
    r"\bexplicit(?:ly)?\s+high[- ]risk\b|\bhigh[- ]risk designation\b|"
    r"\bknown\s+production\s+instability\b|"
    r"\b(?:failed\s+deployment\s+validation|deployment\s+validation\s+failed)\b|"
    r"\b(?:likelihood|classification)\s*:?\s*probable\b",
    re.IGNORECASE,
)


def repair_json_text(text: str) -> dict[str, Any]:
    """Extract one JSON object from raw text without evaluating code."""

    try:
        return extract_json_object(text)
    except JsonParseError:
        raise


def normalize_field_aliases(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize common field aliases without changing business content."""

    repaired = dict(payload)
    for alias, canonical in ALIASES.items():
        if alias in repaired and canonical not in repaired:
            repaired[canonical] = repaired.pop(alias)
    return repaired


def repair_llm_output_shape(payload: dict[str, Any]) -> dict[str, Any]:
    """Repair structural fields required by Phase 5B output models."""

    repaired = normalize_field_aliases(payload)
    for key in ("evidence_used", "missing_information", "generation_notes"):
        value = repaired.get(key)
        if value is None:
            repaired[key] = []
        elif not isinstance(value, list):
            repaired[key] = [str(value)]

    if "model_confidence" in repaired:
        repaired["model_confidence"] = _repair_confidence(repaired["model_confidence"])

    return repaired


def detect_delivery_detail_leakage(text: str) -> bool:
    """Return whether a change-intent field exposes delivery-only metadata."""

    return any(pattern.search(text) for pattern in _DELIVERY_DETAIL_PATTERNS)


def detect_backout_delivery_metadata_leakage(text: str) -> bool:
    """Return whether backout text exposes delivery or release metadata."""

    return any(pattern.search(text) for pattern in _BACKOUT_DELIVERY_METADATA_PATTERNS)


def expected_backout_duration_statement(evidence_bundle: dict[str, Any]) -> str:
    """Return an evidence-grounded, practically rounded backout duration statement."""

    bucket = bucket_3_evidence(evidence_bundle)
    uat_deployment = _dict_value(bucket.get("uat_deployment"))
    duration = uat_deployment.get("total_deployment_duration_seconds")
    if isinstance(duration, bool) or not isinstance(duration, int | float) or duration <= 0:
        return _CONFIRM_BACKOUT_DURATION
    minutes = float(duration) / 60
    if minutes <= 10:
        estimate = "10 minutes"
    elif minutes <= 20:
        estimate = "20 minutes"
    elif minutes <= 30:
        estimate = "30 minutes"
    elif minutes <= 45:
        estimate = "45 minutes"
    elif minutes <= 60:
        estimate = "1 hour"
    else:
        rounded_minutes = int((minutes + 29) // 30 * 30)
        hours, remainder = divmod(rounded_minutes, 60)
        if remainder == 0:
            estimate = f"{hours} hours"
        else:
            estimate = f"{hours} hour{'s' if hours != 1 else ''} {remainder} minutes"
    return f"Estimated backout time: approximately {estimate}."


def repair_bucket_3_fields(
    payload: dict[str, Any],
    evidence_bundle: dict[str, Any],
    fields_to_repair: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Normalize Bucket 3 fields to concise, evidence-grounded ServiceNow text."""

    repaired = dict(payload)
    notes: list[str] = []
    backout = repaired.get("backout_plan")
    repair_backout = fields_to_repair is None or "backout_plan" in fields_to_repair
    if repair_backout and isinstance(backout, str) and backout.strip():
        normalized_backout = _build_backout_plan(backout, evidence_bundle)
        if normalized_backout != backout.strip():
            repaired["backout_plan"] = normalized_backout
            notes.append("Normalized backout plan to evidence-grounded steps and duration.")
    risk = repaired.get("risk_impact_analysis")
    repair_risk = fields_to_repair is None or "risk_impact_analysis" in fields_to_repair
    if repair_risk and isinstance(risk, str) and risk.strip():
        normalized_risk = _build_risk_impact_analysis(evidence_bundle)
        if normalized_risk != risk.strip():
            repaired["risk_impact_analysis"] = normalized_risk
            notes.append("Normalized risk and impact analysis to supported concise statements.")
    return repaired, notes


def repair_change_intent_fields(
    payload: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Conservatively repair delivery leakage and repeated description sentences."""

    repaired = dict(payload)
    notes: list[str] = []
    for field in ("change_description", "justification"):
        value = repaired.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        cleaned = _remove_delivery_detail_sentences(value)
        if cleaned and cleaned != value.strip():
            repaired[field] = cleaned
            notes.append(f"Removed delivery metadata from {field}.")

    change_description = repaired.get("change_description")
    justification = repaired.get("justification")
    if isinstance(change_description, str) and isinstance(justification, str):
        condensed = _remove_repeated_justification_sentences(
            change_description,
            justification,
        )
        if condensed and condensed != justification.strip():
            repaired["justification"] = condensed
            notes.append("Removed description-like sentences from justification.")
    return repaired, notes


def normalized_words(text: str) -> list[str]:
    """Return lowercase word tokens used by conservative overlap checks."""

    return [match.group(0).lower() for match in _WORD_RE.finditer(text)]


def sequence_similarity(first: str, second: str) -> float:
    """Return a normalized word-sequence similarity score."""

    first_words = normalized_words(first)
    second_words = normalized_words(second)
    if not first_words or not second_words:
        return 0.0
    return SequenceMatcher(None, first_words, second_words, autojunk=False).ratio()


def longest_contiguous_word_overlap(first: str, second: str) -> int:
    """Return the longest contiguous word run shared by both values."""

    first_words = normalized_words(first)
    second_words = normalized_words(second)
    if not first_words or not second_words:
        return 0
    match = SequenceMatcher(None, first_words, second_words, autojunk=False).find_longest_match()
    return match.size


def _remove_delivery_detail_sentences(text: str) -> str:
    retained: list[str] = []
    for raw_sentence in _SENTENCE_SPLIT_RE.split(text.strip()):
        sentence = _strip_trailing_delivery_clause(raw_sentence.strip())
        if not sentence:
            continue
        if detect_delivery_detail_leakage(sentence):
            clauses = [part.strip() for part in re.split(r";|,\s+", sentence) if part.strip()]
            safe_clauses = [part for part in clauses if not detect_delivery_detail_leakage(part)]
            sentence = ", ".join(safe_clauses)
        if sentence and not detect_delivery_detail_leakage(sentence):
            retained.append(_restore_terminal_punctuation(sentence, raw_sentence))
    return " ".join(retained).strip()


def _strip_trailing_delivery_clause(sentence: str) -> str:
    cleaned = sentence
    for pattern in _TRAILING_DELIVERY_CLAUSE_PATTERNS:
        cleaned = pattern.sub("", cleaned).rstrip(" ,;")
    return cleaned


def _restore_terminal_punctuation(value: str, original: str) -> str:
    if value.endswith((".", "!", "?")):
        return value
    ending = original.rstrip()[-1:] if original.rstrip() else ""
    return f"{value}{ending}" if ending in ".!?" else value


def _remove_repeated_justification_sentences(
    change_description: str,
    justification: str,
) -> str:
    description_sentences = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_RE.split(change_description.strip())
        if sentence.strip()
    ]
    justification_sentences = [
        sentence.strip()
        for sentence in _SENTENCE_SPLIT_RE.split(justification.strip())
        if sentence.strip()
    ]
    if len(justification_sentences) < 2:
        return justification.strip()

    retained: list[str] = []
    for sentence in justification_sentences:
        sentence_words = normalized_words(sentence)
        repeats_description = len(sentence_words) >= 10 and any(
            sequence_similarity(sentence, description_sentence) >= 0.88
            or " ".join(sentence_words)
            in " ".join(normalized_words(description_sentence))
            for description_sentence in description_sentences
        )
        if not repeats_description:
            retained.append(sentence)

    candidate = " ".join(retained).strip()
    lowered = candidate.lower()
    if (
        candidate
        and len(normalized_words(candidate)) >= 8
        and any(term in lowered for term in _RATIONALE_TERMS)
    ):
        return candidate
    return justification.strip()


def _build_backout_plan(generated_text: str, evidence_bundle: dict[str, Any]) -> str:
    bucket = bucket_3_evidence(evidence_bundle)
    uat_deployment = _dict_value(bucket.get("uat_deployment"))
    activity_names = [
        str(item.get("name") or "")
        for item in uat_deployment.get("activities", [])
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    evidence_text = " ".join(activity_names)
    if not evidence_text:
        evidence_text = generated_text
    steps = _backout_steps_for_actions(evidence_text)
    lines = [f"{index}. {step}" for index, step in enumerate(steps, start=1)]
    lines.append("")
    lines.append(expected_backout_duration_statement(evidence_bundle))
    return "\n".join(lines)


def _backout_steps_for_actions(text: str) -> list[str]:
    lowered = text.lower()
    steps = ["Stop or pause the production deployment."]
    reverse_actions: list[str] = []
    if any(term in lowered for term in ("deploy", "import", "solution", "package", "redeploy")):
        reverse_actions.append(
            "Redeploy the previously validated solution or application package used before "
            "this change."
        )
    if any(
        term in lowered
        for term in ("configuration", "config", "environment variable", "setting")
    ):
        reverse_actions.append(
            "Restore the prior application configuration and environment settings."
        )
    if any(term in lowered for term in ("dependency", "library", "runtime")):
        reverse_actions.append("Restore the prior dependency settings used by the application.")
    if any(term in lowered for term in ("database", "schema", "sql", "migration")):
        reverse_actions.append("Reverse the database deployment actions applied by this change.")
    if any(term in lowered for term in ("infrastructure", "terraform", "bicep", "network")):
        reverse_actions.append("Restore the prior infrastructure configuration.")
    if any(term in lowered for term in ("restart", "start service", "stop service")):
        reverse_actions.append("Restart the impacted application service after restoration.")
    if not reverse_actions:
        reverse_actions.append("Restore the application or configuration to its pre-change state.")
    steps.extend(_dedupe_text(reverse_actions))
    if any(
        term in lowered
        for term in ("validate", "validation", "smoke", "health", "checker", "test")
    ):
        steps.append("Validate the impacted application and its critical functions.")
    return _dedupe_text(steps)


def _build_risk_impact_analysis(evidence_bundle: dict[str, Any]) -> str:
    bucket = bucket_3_evidence(evidence_bundle)
    application = _business_readable_application(bucket)
    likelihood = _likelihood_from_evidence(bucket)
    planned_impact = _planned_impact_statement(bucket)
    risk_scope = _risk_scope(bucket)
    potential_application = (
        "application or service associated with this deployment"
        if application.startswith("Application or service associated")
        else application
    )
    potential = (
        f"Potential impact: The {potential_application} may experience temporary functional "
        "degradation "
        f"in {risk_scope} if the change does not complete successfully."
    )
    mitigation = ""
    uat = _dict_value(bucket.get("uat_deployment"))
    if uat.get("activities") or bucket.get("rollback_indicators"):
        mitigation = " The change can be backed out using the documented backout steps."
    return (
        f"{planned_impact}\n\n"
        f"Impacted application: {application}.\n\n"
        f"Likelihood of unplanned impact: {likelihood}.\n\n"
        f"{potential}{mitigation}"
    )


def _planned_impact_statement(bucket: dict[str, Any]) -> str:
    values = bucket.get("planned_impact_evidence")
    if isinstance(values, list):
        for value in values:
            if not isinstance(value, str) or not value.strip():
                continue
            lowered = value.lower()
            negative = re.search(
                r"\b(?:no|without)\s+(?:planned\s+)?(?:service\s+)?"
                r"(?:outage|downtime|impact|degradation|disruption)\b",
                lowered,
            )
            positive = re.search(
                r"\b(?:will be unavailable|planned\s+(?:service\s+)?(?:outage|downtime|"
                r"impact|degradation|disruption)|expected\s+(?:service\s+)?(?:outage|"
                r"downtime|impact|degradation|disruption)|intermittent access)\b",
                lowered,
            )
            if positive and not negative:
                statement = re.sub(r"^\s*Planned impact\s*:\s*", "", value, flags=re.IGNORECASE)
                statement = _one_concise_sentence(statement)
                return f"Planned impact: {statement}"
    return "Planned impact: No planned service outage is identified."


def _business_readable_application(bucket: dict[str, Any]) -> str:
    candidates = bucket.get("application_candidates")
    if not isinstance(candidates, list):
        candidates = []
    service_context = _dict_value(bucket.get("service_context"))
    candidates = [*candidates, service_context.get("repository_name")]
    impacted = bucket.get("impacted_components")
    if isinstance(impacted, list):
        candidates.extend(impacted)
    for value in candidates:
        if not isinstance(value, str) or not value.strip():
            continue
        cleaned = value.strip().removeprefix("the ").removeprefix("The ")
        if "refs/heads/" in cleaned.lower() or "/" in cleaned or "\\" in cleaned:
            continue
        cleaned = re.sub(r"[-_.]+", " ", cleaned)
        cleaned = re.sub(
            r"\b(?:build|release|deployment)\s+pipeline\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
        if not cleaned:
            continue
        acronym_tokens = {"ado", "api", "asac", "crm", "dod", "ui"}
        words = [
            word.upper() if word.lower() in acronym_tokens else word.capitalize()
            for word in cleaned.split()
        ]
        readable = " ".join(words)
        lowered = readable.lower()
        if lowered.endswith(" api") and "service" not in lowered:
            return f"{readable} service"
        if "application" not in lowered and "service" not in lowered:
            return f"{readable} application"
        return readable
    return (
        "Application or service associated with this deployment; confirmation is required "
        "before change submission"
    )


def _likelihood_from_evidence(bucket: dict[str, Any]) -> str:
    if has_high_risk_evidence(bucket):
        return "Probable"
    if has_resiliency_evidence(bucket):
        return "Improbable"
    return "Possible"


def has_resiliency_evidence(evidence_bundle: dict[str, Any]) -> bool:
    """Return whether Bucket 3 contains explicit resiliency or traffic protection evidence."""

    bucket = bucket_3_evidence(evidence_bundle)
    resiliency = _dict_value(bucket.get("resiliency_evidence"))
    if any(resiliency.get(field) is True for field in _RESILIENCY_BOOL_FIELDS):
        return True
    if (
        isinstance(resiliency.get("alternate_region"), str)
        and resiliency["alternate_region"].strip()
    ):
        return True
    source_text = bucket_3_claim_evidence_text(bucket)
    return bool(
        re.search(
            r"\bactive[- ]active\b|\brolling (?:deployment|update)\b|"
            r"\b(?:alternate|secondary|separate|passive)\s+(?:region|data center|instance)\b|"
            r"\btraffic\b.*\b(?:remain|shift|route|healthy instance)\b",
            source_text,
            re.IGNORECASE,
        )
    )


def has_high_risk_evidence(evidence_bundle: dict[str, Any]) -> bool:
    """Return whether Bucket 3 contains an explicit Probable-class risk signal."""

    bucket = bucket_3_evidence(evidence_bundle)
    values = bucket.get("high_risk_evidence")
    if isinstance(values, list) and any(
        isinstance(value, str) and value.strip() for value in values
    ):
        return True
    return bool(_HIGH_RISK_RE.search(bucket_3_claim_evidence_text(bucket)))


def has_explicit_planned_impact_evidence(evidence_bundle: dict[str, Any]) -> bool:
    """Return whether Bucket 3 explicitly supports a planned outage or degradation."""

    bucket = bucket_3_evidence(evidence_bundle)
    values = bucket.get("planned_impact_evidence")
    if not isinstance(values, list):
        return False
    for value in values:
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        negative = re.search(
            r"\b(?:no|without)\s+(?:planned\s+)?(?:service\s+)?"
            r"(?:outage|downtime|impact|degradation|disruption)\b",
            lowered,
        )
        positive = re.search(
            r"\b(?:will be unavailable|planned\s+(?:service\s+)?(?:outage|downtime|"
            r"impact|degradation|disruption)|expected\s+(?:service\s+)?(?:outage|"
            r"downtime|impact|degradation|disruption)|intermittent access)\b",
            lowered,
        )
        if positive and not negative:
            return True
    return False


def _risk_scope(bucket: dict[str, Any]) -> str:
    flags = _dict_value(bucket.get("risk_flags"))
    scopes: list[str] = []
    if flags.get("database_change_detected") is True:
        scopes.append("database-dependent functionality")
    if flags.get("infrastructure_change_detected") is True:
        scopes.append("infrastructure-hosted components")
    if flags.get("dependency_change_detected") is True:
        scopes.append("dependency-related functionality")
    if flags.get("config_change_detected") is True:
        scopes.append("configuration-dependent behavior")
    if flags.get("feature_flag_change_detected") is True:
        scopes.append("feature-flag-controlled functionality")
    if not scopes:
        return "the components updated by this change"
    if len(scopes) == 1:
        return scopes[0]
    return ", ".join(scopes[:-1]) + f", and {scopes[-1]}"


def bucket_3_claim_evidence_text(evidence_bundle: dict[str, Any]) -> str:
    """Return only evidence-bearing Bucket 3 text, excluding false boolean field names."""

    bucket = bucket_3_evidence(evidence_bundle)
    values: list[str] = []
    for key in (
        "risk_signals",
        "planned_impact_evidence",
        "high_risk_evidence",
        "application_candidates",
    ):
        items = bucket.get(key)
        if isinstance(items, list):
            values.extend(str(item) for item in items if isinstance(item, str))
    failures = bucket.get("failed_or_warning_evidence")
    if isinstance(failures, list):
        for item in failures:
            if isinstance(item, dict):
                values.extend(str(item.get(key) or "") for key in ("name", "message", "result"))
    resiliency = _dict_value(bucket.get("resiliency_evidence"))
    alternate_region = resiliency.get("alternate_region")
    if isinstance(alternate_region, str):
        values.append(alternate_region)
    return " ".join(values)


def bucket_3_evidence(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    """Return Bucket 3 from a bundle or accept an already-scoped Bucket 3 payload."""

    bucket = evidence_bundle.get("bucket_3")
    if isinstance(bucket, dict):
        return bucket
    return evidence_bundle


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _one_concise_sentence(value: str) -> str:
    sentence = _SENTENCE_SPLIT_RE.split(re.sub(r"\s+", " ", value.strip()))[0]
    words = sentence.split()
    if len(words) > 35:
        sentence = " ".join(words[:35]).rstrip(" ,;:")
    if not sentence.endswith((".", "!", "?")):
        sentence += "."
    return sentence


def _dedupe_text(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(value)
    return output


def _repair_confidence(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        try:
            if stripped.endswith("%"):
                return max(0.0, min(float(stripped[:-1]) / 100, 1.0))
            return float(stripped)
        except ValueError:
            return value
    if isinstance(value, (int, float)) and 1 < float(value) <= 100:
        return max(0.0, min(float(value) / 100, 1.0))
    return value
