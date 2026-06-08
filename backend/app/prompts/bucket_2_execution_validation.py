"""Prompt builder for Phase 5B execution and validation fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.1"


def build_prompt(evidence: dict[str, Any], prompt_strategy: str | None = None) -> str:
    """Build the bucket 2 prompt from deterministic evidence only."""

    evidence_json = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)
    strategy = prompt_strategy or "bucket_2_standard"
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
Do not include JSON paths such as raw.timeline.records[5] in field text.
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
- testing_performed
- implementation_plan
- validation_plan

Guidance:
- testing_performed: Summarize what validation/testing happened in lower environments. If
  automated test results exist, summarize test count, pass/fail/skipped totals where available.
  Mention functional, non-functional, scan, or validation evidence only if supported.
- If no test results exist, state that no automated test results were available in the
  collected evidence.
- Automated test results were not available.
- Use this exact business-readable sentence when automated test evidence is absent: "Automated
  test results were not available in the collected Azure DevOps evidence."
- If automated test results are missing, use business-readable wording such as: "Automated test
  results were not available in the collected Azure DevOps evidence. Pipeline validation,
  deployment checks, scans, and available validation signals were reviewed where present.
  Additional validation should be confirmed through the approved release process before
  production deployment."
- Do not say tests passed, all tests passed, or functional testing completed unless evidence
  supports it.
- Do not invent test counts.
- implementation_plan: Describe how the change will be deployed using the approved pipeline,
  build number/build definition when available, deployment sequence from stages/jobs/tasks,
  target environments when available, and artifact/package evidence when available.
- validation_plan: Describe what will be checked during and after deployment, such as service
  health, API validation, smoke tests, logs, dashboards, monitoring, synthetic checks, and
  business validation when supported by evidence.
- If validation evidence is weak, use conservative language.
- Avoid claiming production validation has already happened unless evidence proves it.
{strategy_guidance}

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


def _strategy_guidance(strategy: str) -> str:
    if strategy == "bucket_2_missing_tests":
        return """Strategy-specific guidance:
- Explicitly state that no automated test results were available in collected Azure DevOps
  evidence.
- Do not imply tests passed.
- Use validation, scan, stage, job, task, and pipeline evidence only when available.
- Lower model_confidence appropriately when test evidence is missing."""
    return """Strategy-specific guidance:
- Use the standard execution and validation prompt behavior."""
