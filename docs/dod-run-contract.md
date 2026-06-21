# DoD Run Contract

The DoD run contract is the shared structured input/output contract for
LangGraph SDK calls, LangGraph Server API calls, FastAPI local/dev calls, CLI
scripts, and future ADO pipeline integration.

The shared models live in `backend/app/models/dod_contracts.py`.

## Input

```json
{
  "organization": "ado-org",
  "project": "ado-project",
  "build_id": 123456,
  "mode": "pipeline",
  "correlation_id": "ado-build-123456",
  "metadata": {
    "source": "ado-pipeline"
  }
}
```

Fields:

- `organization`: required non-empty Azure DevOps organization.
- `project`: required non-empty Azure DevOps project.
- `build_id`: required positive build id.
- `mode`: optional, defaults to `pipeline`.
- `correlation_id`: optional caller correlation id.
- `requested_by`: optional caller identity or service name.
- `source`: optional integration source.
- `metadata`: optional structured caller metadata, defaults to `{}`.

Allowed modes:

- `pipeline`
- `local`
- `replay`
- `api`

## Output

```json
{
  "run_id": "dod-123456-...",
  "build_id": 123456,
  "status": "completed_with_warnings",
  "service_now_payload": {},
  "confidence": {},
  "rule_evaluation_summary": {
    "highest_severity": "warning",
    "recommended_status": "completed_with_warnings",
    "triggered_rule_count": 3
  },
  "artifact_paths": {
    "service_now_payload": "data/output/123456/service_now_payload.json",
    "rule_evaluation": "data/output/123456/rule_evaluation.json",
    "traceability_report": "data/output/123456/traceability_report.json"
  },
  "warnings": [],
  "errors": []
}
```

Status values are compatible with the existing application behavior:

- `completed`
- `completed_with_warnings`
- `needs_review`
- `failed`
- `error`

`service_now_payload` is included for existing downstream compatibility, but
safe summaries should not print it by default. Full artifacts such as evidence
bundles, raw Azure DevOps payloads, LLM outputs, traceability reports, and rule
evaluation files are stored separately and should be retrieved through explicit
artifact APIs or storage paths when needed.

## Invocation Notes

LangGraph production calls should use structured input, not messages-only input.
This keeps build identity, correlation, and metadata stable across SDK, server
API, FastAPI, CLI, and future pipeline callers.

The LangGraph deployment graph remains:

```text
dod: backend/app/graphs/dod_deployment_graph.py:make_graph_dod
```

The graph calls only the existing `run_dod_agent` orchestration service. It does
not directly call Azure DevOps, Azure OpenAI, Cosmos DB, or ServiceNow.

Cosmos artifact persistence is selected through `DOD_STORAGE_BACKEND`. The graph
and contract layer do not call Cosmos directly.
