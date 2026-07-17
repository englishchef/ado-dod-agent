"""Shared deterministic selectors for Bucket 3 deployment and application evidence."""

from __future__ import annotations

import math
import re

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

_NON_DEPLOYMENT_ACTIVITY_PATTERNS = (
    re.compile(r"\bget\s+(?:base\s+)?solution\s+versions?\b", re.IGNORECASE),
    re.compile(r"\b(?:download|publish)\s+(?:build\s+)?artifacts?\b", re.IGNORECASE),
    re.compile(r"\bartifact\s+(?:download|publish|upload)\b", re.IGNORECASE),
    re.compile(r"\b(?:checkout|initialize|initialization)\b", re.IGNORECASE),
    re.compile(r"\b(?:approval|approve|manual validation)\b", re.IGNORECASE),
    re.compile(r"\b(?:wait|delay|sleep)\b", re.IGNORECASE),
    re.compile(r"\b(?:authenticate|authentication|login|sign in)\b", re.IGNORECASE),
    re.compile(r"\b(?:discover|discovery)\s+(?:the\s+)?environment\b", re.IGNORECASE),
    re.compile(r"\b(?:resolve|load|set)\s+(?:pipeline\s+)?variables?\b", re.IGNORECASE),
    re.compile(r"\b(?:metadata|diagnostic|diagnostics)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:run|execute)\s+(?:unit|integration|functional|regression)\s+tests?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:solution checker|validate|validation|health check|smoke test)\b",
        re.IGNORECASE,
    ),
)
_DEPLOYMENT_ACTIVITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "solution_upgrade",
        re.compile(
            r"\b(?:apply\s+solution\s+upgrade|upgrade\s+solution|apply\s+upgrade)\b",
            re.IGNORECASE,
        ),
    ),
    ("solution_import", re.compile(r"\bimport\s+solution\b", re.IGNORECASE)),
    ("solution_deploy", re.compile(r"\bdeploy\s+solution\b", re.IGNORECASE)),
    (
        "application_deploy",
        re.compile(r"\bdeploy\s+(?:application|app|service)\b", re.IGNORECASE),
    ),
    (
        "package_deploy",
        re.compile(r"\b(?:install|deploy)\s+(?:application\s+)?package\b", re.IGNORECASE),
    ),
    (
        "customization_publish",
        re.compile(r"\bpublish\s+customizations?\b", re.IGNORECASE),
    ),
    (
        "configuration_apply",
        re.compile(
            r"\b(?:update|apply)\s+(?:(?:application|environment)\s+)?configuration\b",
            re.IGNORECASE,
        ),
    ),
    (
        "infrastructure_deploy",
        re.compile(r"\bdeploy\s+infrastructure\b", re.IGNORECASE),
    ),
    (
        "database_deploy",
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


def deployment_action_kind(name: str | None) -> str | None:
    """Classify a real deployment action while excluding preparation and validation tasks."""

    text = (name or "").strip()
    if not text or any(pattern.search(text) for pattern in _NON_DEPLOYMENT_ACTIVITY_PATTERNS):
        return None
    for kind, pattern in _DEPLOYMENT_ACTIVITY_PATTERNS:
        if pattern.search(text):
            return kind
    return None


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
