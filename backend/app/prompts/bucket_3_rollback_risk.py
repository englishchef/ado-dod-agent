"""Prompt builder for Phase 5B rollback and risk fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.1"


def build_prompt(evidence: dict[str, Any], prompt_strategy: str | None = None) -> str:
    """Build the bucket 3 prompt from deterministic evidence only."""

    evidence_json = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)
    strategy = prompt_strategy or "bucket_3_standard"
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
Do not include JSON paths such as canonical.change_context.commits[0] in field text.
Do not include canonical paths, evidence paths, source_ref values, or bracketed evidence
identifiers inside field text.
Do not mention evidence keys, JSON paths, raw payload names, source_ref, source_ref_map, or
internal bucket names in field text.
Use evidence references only in the evidence_used array.
evidence_used should contain friendly source refs where available, such as work_item:12345,
commit:9f3a21b, pipeline_task:Run_Functional_Tests, or artifact:drop.
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
- backout_plan
- risk_impact_analysis

Guidance:
- backout_plan: Describe how to revert if an issue occurs. Use previous known-good version,
  prior artifact, build/source version, rollback pipeline, redeployment strategy, revert commit,
  or feature flag fallback where supported by evidence.
- If explicit rollback evidence is missing, generate a conservative rollback plan and state that
  explicit rollback validation evidence was not available. Do not claim rollback was tested.
- risk_impact_analysis: Describe expected risk level, affected services/components,
  customer/system impact, traffic or availability impact when evidence supports it, uncertainty
  due to missing evidence, and risk flags such as config, database, infrastructure, dependency,
  or feature flag changes.
- Do not say no risk, zero risk, or no impact. Use "No specific risk signals were detected in
  the collected evidence." instead of absolute language.
- No specific risk signals were detected in the collected evidence.
- Preferred non-absolute wording: "No specific risk signals were detected in the collected
  evidence."
- If tests are missing, reflect that as a risk/uncertainty.
- If risk flags are false, say no evidence of that category was detected, not that the risk is
  impossible.
- Say not that the risk is impossible.
{strategy_guidance}

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


def _strategy_guidance(strategy: str) -> str:
    if strategy == "bucket_3_conservative_rollback":
        return """Strategy-specific guidance:
- If no explicit rollback task exists, generate a conservative rollback plan based on the
  previous known-good version or a revert/redeploy approach.
- Clearly mark missing explicit rollback evidence in missing_information.
- Do not claim rollback was tested or rollback validation completed."""
    if strategy == "bucket_3_high_risk":
        return """Strategy-specific guidance:
- Explicitly reflect database, infrastructure, dependency, feature flag, and configuration
  risk flags when present.
- Recommend careful validation and manual review language when supported by evidence.
- Do not overstate certainty or say there is no risk, zero risk, or no impact."""
    return """Strategy-specific guidance:
- Use the standard rollback and risk prompt behavior."""
