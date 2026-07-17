"""Shared deterministic selectors for Bucket 3 deployment and application evidence."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

ENVIRONMENT_PRIORITY = ("UAT", "QA", "TEST", "INTG", "SIT", "DEV")

_ENVIRONMENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "UAT",
        re.compile(
            r"\b(?:uat|user[\s_-]+acceptance[\s_-]+test(?:ing)?)\b",
            re.IGNORECASE,
        ),
    ),
    ("QA", re.compile(r"\b(?:qa|quality[\s_-]+assurance)\b", re.IGNORECASE)),
    ("TEST", re.compile(r"\b(?:test|testing)\b", re.IGNORECASE)),
    (
        "INTG",
        re.compile(r"\b(?:intg|integration)\b", re.IGNORECASE),
    ),
    ("SIT", re.compile(r"\bsit\b|\bsystem[\s_-]+integration[\s_-]+test\b", re.IGNORECASE)),
    (
        "DEV",
        re.compile(r"\b(?:dev|development)\b", re.IGNORECASE),
    ),
)
_PREPRODUCTION_RE = re.compile(
    r"\b(?:non|pre)[\s_-]?prod(?:uction)?\b",
    re.IGNORECASE,
)
_OTHER_LOWER_ENVIRONMENT_RE = re.compile(
    r"\b(?:staging|sandbox|lower[\s_-]+environment)\b",
    re.IGNORECASE,
)
_PRODUCTION_RE = re.compile(r"\b(?:prod|production)\b", re.IGNORECASE)
_NON_DEPLOYMENT_STAGE_RE = re.compile(
    r"\b(?:build|compile|artifact|scan|approval)[\s_-]*(?:only|stage)?\b|"
    r"\b(?:unit|functional|regression|smoke|automated)[\s_-]+tests?\b|"
    r"\btest[\s_-]+only\b",
    re.IGNORECASE,
)

_NON_DEPLOYMENT_ACTIVITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "metadata_lookup",
        re.compile(
            r"\b(?:get\s+(?:base\s+)?solution\s+versions?|get\s+solution\s+version|"
            r"metadata\s+(?:lookup|retrieval)|environment\s+discovery|variable\s+resolution)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "preparation",
        re.compile(
            r"\b(?:download|publish|upload)\s+(?:build\s+)?artifacts?\b|"
            r"\bartifact\s+(?:download|publish|upload)\b|"
            r"\b(?:checkout|initialize|initialization|authenticate|authentication|"
            r"login|sign in|validate connection)\b",
            re.IGNORECASE,
        ),
    ),
    ("approval", re.compile(r"\b(?:approval|approve|manual validation)\b", re.IGNORECASE)),
    ("wait", re.compile(r"\b(?:wait|delay|sleep)\b", re.IGNORECASE)),
    (
        "diagnostic",
        re.compile(r"\b(?:diagnostic|diagnostics|environment discovery)\b", re.IGNORECASE),
    ),
    (
        "test",
        re.compile(
            r"\b(?:run|execute)\s+(?:unit|integration|functional|regression)\s+tests?\b|"
            r"\bsolution checker\b",
            re.IGNORECASE,
        ),
    ),
    (
        "deployment_validation",
        re.compile(
            r"\b(?:validate|validation|verify|health check|smoke test)\b",
            re.IGNORECASE,
        ),
    ),
)
_DEPLOYMENT_ACTIVITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "solution_upgrade",
        re.compile(
            r"\b(?:apply\s+solution\s+upgrade|upgrade\s+solution|apply\s+upgrade|"
            r"pac\s+solution\s+upgrade)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "solution_deployment",
        re.compile(
            r"\b(?:import|deploy)\s+solution\b|\bpower\s+platform\s+import\s+solution\b|"
            r"\bpac\s+solution\s+import\b",
            re.IGNORECASE,
        ),
    ),
    (
        "application_deployment",
        re.compile(r"\bdeploy\s+(?:application|app|service)\b", re.IGNORECASE),
    ),
    (
        "package_deployment",
        re.compile(r"\b(?:install|deploy)\s+(?:application\s+)?package\b", re.IGNORECASE),
    ),
    (
        "customization_publish",
        re.compile(r"\bpublish\s+customizations?\b", re.IGNORECASE),
    ),
    (
        "configuration_change",
        re.compile(
            r"\b(?:update|apply)\s+(?:(?:application|environment)\s+)?configuration\b",
            re.IGNORECASE,
        ),
    ),
    (
        "infrastructure_change",
        re.compile(r"\bdeploy\s+infrastructure\b", re.IGNORECASE),
    ),
    (
        "database_change",
        re.compile(r"\bdatabase\s+deployment\b|\bdeploy\s+database\b", re.IGNORECASE),
    ),
    (
        "service_restart",
        re.compile(
            r"\brestart\s+(?:the\s+)?(?:application|app|service)\b",
            re.IGNORECASE,
        ),
    ),
)

_DEPLOYMENT_ACTIONS = frozenset(kind for kind, _ in _DEPLOYMENT_ACTIVITY_PATTERNS)

BACKOUT_STEP_BY_ACTION: dict[str, str] = {
    "solution_deployment": "Redeploy the previously validated solution version.",
    "solution_upgrade": (
        "Apply the prior solution version and complete the solution rollback."
    ),
    "application_deployment": "Redeploy the previously validated application version.",
    "package_deployment": "Redeploy the previously validated package.",
    "configuration_change": "Restore the previous configuration settings.",
    "infrastructure_change": "Restore the prior infrastructure configuration.",
    "database_change": (
        "Restore the prior database deployment or execute the documented database "
        "rollback procedure."
    ),
    "service_restart": "Restart the affected application service after restoration.",
    "customization_publish": "Republish the restored customizations.",
    "deployment_validation": "Validate application health and affected business workflows.",
}


@dataclass(frozen=True)
class DeploymentActionClassification:
    """Deterministic classification and the ordered signal names that supported it."""

    classification: str
    classification_evidence: tuple[str, ...] = ()

    @property
    def is_deployment_action(self) -> bool:
        return self.classification in _DEPLOYMENT_ACTIONS

    @property
    def generates_backout_step(self) -> bool:
        return self.classification in BACKOUT_STEP_BY_ACTION

_GENERIC_APPLICATION_WORDS = re.compile(
    r"\b(?:build|pipeline|deploy|deployment|release|service[\s_-]+connection|"
    r"application|service)\b",
    re.IGNORECASE,
)
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def normalize_environment_name(name: str | None) -> str | None:
    """Return the canonical environment label represented by a stage or job name."""

    text = name or ""
    if _PREPRODUCTION_RE.search(text):
        return "OTHER"
    if _PRODUCTION_RE.search(text):
        return "PRODUCTION"
    for environment, pattern in _ENVIRONMENT_PATTERNS:
        if pattern.search(text):
            return environment
    if _OTHER_LOWER_ENVIRONMENT_RE.search(text):
        return "OTHER"
    return None


def environment_priority(environment: str | None) -> int:
    """Return a stable selection priority, with unrecognized lower environments last."""

    if environment in ENVIRONMENT_PRIORITY:
        return ENVIRONMENT_PRIORITY.index(environment)
    if environment == "OTHER":
        return len(ENVIRONMENT_PRIORITY)
    return len(ENVIRONMENT_PRIORITY) + 1


def is_production_name(name: str | None) -> bool:
    """Return whether a name explicitly identifies Production."""

    return normalize_environment_name(name) == "PRODUCTION"


def is_non_deployment_stage_name(name: str | None) -> bool:
    """Return whether a stage is explicitly build, scan, approval, artifact, or test-only."""

    return bool(_NON_DEPLOYMENT_STAGE_RE.search(name or ""))


def deployment_action_kind(name: str | None) -> str | None:
    """Classify a real deployment action while excluding preparation and validation tasks."""

    classification = classify_deployment_action(name=name)
    return classification.classification if classification.is_deployment_action else None


def classify_deployment_action(
    *,
    name: str | None,
    task_type: str | None = None,
    task_definition: str | None = None,
    description: str | None = None,
    command: str | None = None,
    inputs: Mapping[str, str] | None = None,
    parent_context: Sequence[str] | None = None,
    log_summary: str | None = None,
) -> DeploymentActionClassification:
    """Classify an activity using ordered evidence without inferring unsupported meaning."""

    input_values = inputs or {}
    input_groups = (
        ("inputs", _input_values(input_values, tuple(input_values))),
        ("package_path", _input_values(input_values, ("package", "packagepath"))),
        ("solution_name", _input_values(input_values, ("solution", "solutionname"))),
        (
            "environment_target",
            _input_values(input_values, ("environment", "environmenttarget", "targetenvironment")),
        ),
    )
    ordered_signals: list[tuple[str, str]] = [
        ("display_name", name or ""),
        ("task_type", task_type or ""),
        ("task_definition", task_definition or ""),
        ("description", description or ""),
        ("command", command or ""),
    ]
    for signal_name, values in input_groups:
        ordered_signals.extend((signal_name, value) for value in values)
    # Parent context can corroborate a recognized signal, but cannot assign meaning by itself.
    context_text = " ".join(value for value in (parent_context or ()) if value)
    for signal_name, text in ordered_signals:
        classification = _classify_activity_text(text)
        if classification != "unknown":
            evidence = [signal_name]
            if context_text and _classify_activity_text(context_text) == classification:
                evidence.append("parent_context")
            return DeploymentActionClassification(classification, tuple(evidence))

    classification = _classify_activity_text(log_summary or "")
    if classification != "unknown":
        return DeploymentActionClassification(classification, ("log_summary",))
    return DeploymentActionClassification("unknown")


def _input_values(inputs: Mapping[str, str], keys: Sequence[str]) -> list[str]:
    normalized_keys = {re.sub(r"[^a-z]", "", key.lower()) for key in keys}
    return [
        value
        for key, value in inputs.items()
        if re.sub(r"[^a-z]", "", key.lower()) in normalized_keys and value.strip()
    ]


def _classify_activity_text(text: str) -> str:
    candidate = text.strip()
    if not candidate:
        return "unknown"
    for classification, pattern in _NON_DEPLOYMENT_ACTIVITY_PATTERNS:
        if pattern.search(candidate):
            return classification
    for classification, pattern in _DEPLOYMENT_ACTIVITY_PATTERNS:
        if pattern.search(candidate):
            return classification
    return "unknown"


def backout_step_for_action(action: str) -> str | None:
    """Return the supported business-readable rollback step for one normalized action."""

    return BACKOUT_STEP_BY_ACTION.get(action)


def is_deployment_activity_name(name: str | None) -> bool:
    """Return whether the activity can drive deterministic backout steps."""

    return deployment_action_kind(name) is not None


def is_explicit_deployment_container_name(name: str | None) -> bool:
    """Return whether a stage or job name explicitly describes deployment to an environment."""

    text = name or ""
    return bool(
        re.search(r"\b(?:deploy|deployment|release)\b", text, re.IGNORECASE)
        and normalize_environment_name(text) not in {None, "PRODUCTION"}
    )


def round_up_backout_minutes(duration_seconds: float | int | None) -> int | None:
    """Round a positive stage duration up to a practical five-minute interval."""

    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int | float):
        return None
    if duration_seconds <= 0:
        return None
    return max(5, int(math.ceil(float(duration_seconds) / 300.0) * 5))


def format_backout_minutes(minutes: int) -> str:
    """Format rounded minutes without seconds or false precision."""

    if minutes < 60:
        return f"{minutes} minutes"
    hours, remainder = divmod(minutes, 60)
    hour_text = f"{hours} hour{'s' if hours != 1 else ''}"
    return hour_text if remainder == 0 else f"{hour_text} {remainder} minutes"


def normalize_application_candidate(value: str | None) -> str:
    """Normalize candidate identity for deterministic comparison and deduplication."""

    text = _CAMEL_BOUNDARY_RE.sub(" ", (value or "").strip())
    text = text.replace("_", " ").replace("-", " ").replace(".", " ")
    text = _GENERIC_APPLICATION_WORDS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -_")
    return text.casefold()


def display_application_name(value: str | None) -> str:
    """Return one business-readable application or service display name."""

    raw = (value or "").strip()
    normalized = normalize_application_candidate(raw)
    if not normalized:
        return "Deployed application"
    acronyms = {"ado", "api", "asac", "crm", "dod", "ui", "uat", "qa", "sit"}
    words = [word.upper() if word in acronyms else word.capitalize() for word in normalized.split()]
    readable = " ".join(words)
    lowered = readable.casefold()
    if re.search(r"\bservice\s*$", raw, re.IGNORECASE) or lowered.endswith(" api"):
        return f"{readable} service"
    return f"{readable} application"
