"""Prompt helper for optional Phase 6 JSON-shape repair."""

from __future__ import annotations

PROMPT_VERSION = "1.1"


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


def build_change_intent_repair_prompt(
    invalid_payload: str,
    validation_issues: list[str],
) -> str:
    """Build a content-repair prompt for separated change-intent fields."""

    issue_text = "\n".join(f"- {issue}" for issue in validation_issues)
    return f"""Repair only change_description and justification in the provided JSON payload.
Return valid JSON only and preserve every other field and metadata value exactly.
Use only facts supported by the existing payload and its supplied evidence context.
Do not invent business impact, operational consequences, benefits, or technical facts.
Do not include markdown, headings, raw evidence references, JSON paths, or evidence keys.

For change_description:
- Remove build numbers, build IDs, pipeline and branch names, artifacts, commit details, CI/CD
  mechanics, deployment steps, test execution, and rollback details.
- Retain the production application or service name, legitimate technical functionality,
  functional enhancements, defect corrections, affected behavior, and production outcome.
- Keep rationale primarily in justification.

For justification:
- Condense any repeated description and do not repeat the full feature or defect list.
- Explain the supported problem or risk, why the existing behavior is insufficient, and the
  supported reliability, correctness, compliance, efficiency, supportability, user-experience,
  or business benefit.
- Keep justification materially distinct from and shorter than change_description.
- Do not add delivery mechanics, testing details, or implementation steps.

Validation issues to repair:
{issue_text or "- Field-purpose separation requires repair."}

Invalid payload:
{invalid_payload}"""
