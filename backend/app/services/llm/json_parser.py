"""Defensive JSON object extraction for LLM responses."""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.services.llm.azure_foundry_client import LlmClientError


class JsonParseError(LlmClientError):
    """Raised when an LLM response cannot be parsed as one JSON object."""


def extract_json_object(text: str) -> dict[str, Any]:
    """Extract and parse a JSON object from raw LLM text."""

    candidates = _candidate_json_strings(text)
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
        raise JsonParseError("LLM response JSON was not an object.")

    raise JsonParseError("LLM response did not contain a valid JSON object.")


def _candidate_json_strings(text: str) -> list[str]:
    stripped = text.strip()
    candidates = [stripped]

    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        candidates.append(fenced_match.group(1).strip())

    object_text = _extract_balanced_object(stripped)
    if object_text is not None:
        candidates.append(object_text)

    return candidates


def _extract_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None
