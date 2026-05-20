"""Prompt builder for Phase 5B execution and validation fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.0"


def build_prompt(evidence: dict[str, Any]) -> str:
    """Build the bucket 2 prompt from deterministic evidence only."""

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
- testing_performed
- implementation_plan
- validation_plan

Guidance:
- Testing performed should summarize available test, scan, validation, and quality evidence.
- If no test results exist, state that no automated test results were available in the
  collected evidence.
- Do not invent test counts.
- Implementation plan should summarize pipeline/deployment sequence using stage/job/task/artifact
  evidence.
- Validation plan should summarize how the deployment should be validated using available
  validation signals.
- If validation evidence is weak, use conservative language.
- Avoid claiming production validation has already happened unless evidence proves it.

Required JSON shape:
{{
  "target_fields": ["testing_performed", "implementation_plan", "validation_plan"],
  "testing_performed": "...",
  "implementation_plan": "...",
  "validation_plan": "...",
  "evidence_used": ["..."],
  "missing_information": ["..."],
  "model_confidence": 0.0,
  "generation_notes": ["..."]
}}

Evidence:
{evidence_json}"""
