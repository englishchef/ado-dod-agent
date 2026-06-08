"""Prompt builder for Phase 5B change intent fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.1"


def build_prompt(evidence: dict[str, Any], prompt_strategy: str | None = None) -> str:
    """Build the bucket 1 prompt from deterministic evidence only."""

    evidence_json = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)
    strategy = prompt_strategy or "bucket_1_standard"
    strategy_guidance = _strategy_guidance(strategy)
    return f"""You are generating ServiceNow-ready business verbiage for change management.
Use only the provided evidence.
Do not invent facts.
If evidence is missing, explicitly include that in missing_information.
The final generated field values must be suitable for direct insertion into ServiceNow.
Use concise, enterprise change-management language.
Use complete sentences.
Use production-release wording.
Do not mention internal implementation details of the DoD agent.
Do not mention Azure DevOps API internals.
Do not include markdown.
Return valid JSON only.
Do not include raw source references in field text.
Do not include JSON paths such as raw.changes.value[3] in field text.
Do not include canonical paths, evidence paths, source_ref values, or bracketed evidence
identifiers inside field text.
Do not mention evidence keys, JSON paths, raw payload names, source_ref, source_ref_map, or
internal bucket names in field text.
Use evidence references only in the evidence_used array.
evidence_used should contain friendly source refs where available, such as work_item:12345,
commit:9f3a21b, or pipeline_task:Run_Functional_Tests.
evidence_used must not be copied into field text.
If evidence is missing, mention it only in business-readable language.
Do not claim tests passed unless test evidence proves it.
Do not invent test results.
Do not claim rollback was tested unless evidence proves it.
Do not claim no risk or no impact absolutely.
If a field has weak evidence, write conservative language instead of inventing.
Keep model_confidence between 0 and 1.
Selected prompt strategy: {strategy}

Target fields:
- change_description
- short_change_description
- justification

Guidance:
- change_description: Describe the technical change in business-readable terms. Include what
  component or service is changing, what is being changed, why it matters operationally or
  technically, and deployment/build context when available. Do not include raw evidence
  references, internal JSON/source paths, commit IDs unless explicitly useful, or source_ref
  strings.
- change_description must identify what component or service is changing.
- short_change_description: Generate a concise one-line title. Prefer styles such as
  "Update of <component/service> <change purpose>",
  "Deployment of <component/service> <release/change>", or
  "Upgrade of <platform/component>".
- justification: Explain why the change is needed using evidence for performance, security,
  supportability, vendor currency, defect remediation, operational stability, compliance,
  business continuity, or environment consistency.
- If PR metadata is absent but work items/commits exist, do not treat that as fatal.
- If justification evidence is weak, be conservative and say it is inferred from available work
  item or commit evidence.
- Do not include unsupported business benefits.
{strategy_guidance}

Required JSON shape:
{{
  "target_fields": ["change_description", "short_change_description", "justification"],
  "change_description": "...",
  "short_change_description": "...",
  "justification": "...",
  "evidence_used": ["..."],
  "missing_information": ["..."],
  "model_confidence": 0.0,
  "generation_notes": ["..."]
}}

Evidence:
{evidence_json}"""


def _strategy_guidance(strategy: str) -> str:
    if strategy == "bucket_1_low_evidence":
        return """Strategy-specific guidance:
- Use conservative wording because change-intent evidence is weak.
- State missing work item or PR metadata only in business-readable language.
- Avoid strong business justification if only commit evidence exists.
- Put missing work item, PR, or business context in missing_information."""
    return """Strategy-specific guidance:
- Use the standard change-intent prompt behavior."""
