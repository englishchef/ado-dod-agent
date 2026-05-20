"""Prompt builder for Phase 5B change intent fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.0"


def build_prompt(evidence: dict[str, Any]) -> str:
    """Build the bucket 1 prompt from deterministic evidence only."""

    evidence_json = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)
    return f"""You are generating ServiceNow-ready change management text.
Use only the provided evidence.
Do not invent facts.
If evidence is missing, explicitly include that in missing_information.
Do not claim tests passed unless test evidence proves it.
Do not claim rollback was tested unless evidence proves it.
Do not mention Azure DevOps API internals.
Do not include markdown.
Return valid JSON only.
Use concise, enterprise-ready language.
Include evidence references from evidence_references/source_ref where available.
If a field has weak evidence, write conservative language instead of inventing.
Keep model_confidence between 0 and 1.

Target fields:
- change_description
- short_change_description
- justification

Guidance:
- Change description should summarize what changed using work item, PR, and commit evidence.
- Short change description should be short and suitable for ServiceNow short description.
- Justification should explain why the change is needed using work item business value,
  acceptance criteria, tags, PR description, or commit intent.
- If PR metadata is absent but work items/commits exist, do not treat that as fatal.
- If only commit evidence exists, say the justification is inferred from available
  implementation evidence.
- Do not include unsupported business benefits.

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
