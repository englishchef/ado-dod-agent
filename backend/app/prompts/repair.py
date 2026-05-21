"""Prompt helper for optional Phase 6 JSON-shape repair."""

from __future__ import annotations

PROMPT_VERSION = "1.0"


def build_repair_prompt(invalid_payload: str, target_schema_name: str) -> str:
    """Build an optional repair prompt that fixes JSON shape only."""

    return f"""Fix the JSON shape so it conforms to {target_schema_name}.
Return valid JSON only.
Do not add business facts.
Do not rewrite field content unless required for schema compliance.
Do not invent evidence.
Do not include markdown.

Invalid payload:
{invalid_payload}"""
