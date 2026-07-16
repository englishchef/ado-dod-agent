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
