"""Prompt builder for Phase 5B rollback and risk fields."""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "1.2"
NON_ABSOLUTE_RISK_WORDING = "No specific risk signals were detected in the collected evidence"


def build_prompt(evidence: dict[str, Any], prompt_strategy: str | None = None) -> str:
    """Build the bucket 3 prompt from deterministic evidence only."""

    evidence_json = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False)
    strategy = prompt_strategy or "bucket_3_standard"
    strategy_guidance = _strategy_guidance(strategy)
    return f"""You are generating ServiceNow-ready business verbiage for change management.
Use only the provided evidence.
Do not invent facts.
If evidence is missing, include it only in missing_information, never in the final field text.
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
Do not claim tests passed unless test evidence proves it.
Do not invent test results.
Do not claim rollback was tested unless evidence proves it.
If a field has weak evidence, write conservative language instead of inventing.
Keep model_confidence between 0 and 1.
Selected prompt strategy: {strategy}

Target fields:
- backout_plan
- risk_impact_analysis

Guidance:
backout_plan field intent:
- Answer only: What actionable steps reverse the production change, and approximately how long
  will the backout take?
- Derive reverse steps primarily from uat_deployment.activities because those activities reflect
  the technical deployment actions observed in UAT.
- Convert UAT solution or package deployment, configuration changes, dependency changes, service
  restarts, database or infrastructure deployment, and validation activities into concise reverse
  actions. Include database or infrastructure steps only when explicitly present.
- Format the actions as a short numbered list followed by exactly one duration line beginning
  "Estimated backout time:".
- Base the duration on uat_deployment.total_deployment_duration_seconds and round it to a practical
  estimate such as approximately 10, 20, 30, or 45 minutes, or approximately 1 hour.
- If reliable UAT timing is unavailable, use exactly: "Estimated backout time: To be confirmed by
  the implementation team before change execution." Do not invent an estimated duration.
- Do not include build IDs, build numbers, version numbers, branch names, pipeline names, artifact
  names, Azure DevOps terminology, source commits, CI/CD details, release package metadata,
  stakeholder coordination, business justification, risk analysis, test-result discussion,
  missing-evidence commentary, or speculative fix-forward steps.
- Never put statements such as "explicit rollback validation evidence was not available" in
  backout_plan. Missing evidence belongs only in missing_information.
- Do not claim rollback was tested or rollback validation completed unless evidence proves it.

risk_impact_analysis field intent:
- Use short labeled statements for Planned impact, Impacted application, Likelihood of unplanned
  impact, and Potential impact. Add one brief mitigation or backout sentence only when supported.
- Keep the field concise, normally approximately 60-140 words. Do not write a long narrative,
  detailed mitigation section, deployment explanation, or worst-case scenario section.
- Planned impact must come from explicit evidence. No planned outage or degradation should be
  assumed merely because the change is deployed to production.
- When evidence does not explicitly identify an outage, degradation, disruption, or downtime, use
  "Planned impact: No planned service outage is identified."
- Identify a business-readable application or service from application_candidates,
  impacted_components, or service_context.repository_name. Do not expose an engineering pipeline
  name. If it cannot be determined, require confirmation without inventing a name.
- Use only Probable, Possible, or Improbable for likelihood. Do not use numeric percentages.
- If evidence does not explicitly support Probable or Improbable, classify likelihood as Possible.
- Improbable requires explicit evidence of active redundancy, alternate-region support, traffic
  protection, rolling deployment, or equivalent resiliency.
- Probable requires explicit evidence of recurring deployment failures, repeated incidents,
  unresolved critical defects, failed deployment validation, known production instability, or an
  explicit high-risk or probable designation. Missing tests, missing evidence, configuration or
  dependency changes, and deployment complexity do not support Probable.
- Passing tests, successful UAT, an available backout, a small change, or no planned outage do not
  support Improbable.
- Describe only one realistic, application-specific potential impact. Do not invent outages,
  member impact, data loss, regional failover, redundancy, recovery capability, authentication or
  secret failures, database corruption, or complete service failure.
- A supported mitigation must be one brief statement and must not repeat the full backout plan.
- Do not include build, artifact, branch, pipeline, commit, or release metadata.
- Do not say no risk, zero risk, or no impact. "{NON_ABSOLUTE_RISK_WORDING}" is non-absolute
  wording, not permission to say that the risk is impossible; say not that the risk is impossible.
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
- Use UAT deployment activities for reverse steps when present.
- If explicit reversal detail is absent, keep the plan operational and conservative without
  inserting build, artifact, version, pipeline, or missing-evidence commentary.
- Put missing rollback evidence only in missing_information.
- Do not claim rollback was tested or rollback validation completed."""
    if strategy == "bucket_3_high_risk":
        return """Strategy-specific guidance:
- Reflect an explicit risk flag only as a concise, realistic potential impact; do not expand it
  into speculative failure scenarios.
- High risk routing does not by itself make likelihood Probable. Probable still requires the
  explicit high-risk evidence described above.
- Do not overstate certainty or say there is no risk, zero risk, or no impact."""
    return """Strategy-specific guidance:
- Use the standard rollback and risk prompt behavior."""
