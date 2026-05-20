"""Prompt builder for Phase 5B rollback and risk fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.0"


def build_prompt(evidence: dict[str, Any]) -> str:
    """Build the bucket 3 prompt from deterministic evidence only."""

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
- backout_plan
- risk_impact_analysis

Guidance:
- Backout plan should use artifacts, source version, rollback indicators, and deployment evidence.
- If no explicit rollback task exists, generate a conservative rollback plan based on
  redeploying the previous known-good version or reverting the current deployment, and mark that
  explicit rollback evidence was not available.
- Risk/impact analysis should use risk flags, risk signals, impacted components,
  failed/warning evidence, and missing context.
- Do not claim rollback has been tested unless evidence proves it.
- If tests are missing, reflect that as a risk/uncertainty.
- If risk flags are false, say no evidence of that category was detected, not that the risk is
  impossible.

Required JSON shape:
{{
  "target_fields": ["backout_plan", "risk_impact_analysis"],
  "backout_plan": "...",
  "risk_impact_analysis": "...",
  "evidence_used": ["..."],
  "missing_information": ["..."],
  "model_confidence": 0.0,
  "generation_notes": ["..."]
}}

Evidence:
{evidence_json}"""
