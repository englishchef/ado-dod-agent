# LangGraph Deployment

Phase 10A exposes the existing DoD agent as a LangGraph-native assistant without
changing the FastAPI, CLI, orchestration, or storage behavior. Phase 10B hardens
the shared structured run contract used by LangGraph, FastAPI, and CLI callers.

## Graph Registration

- Graph name: `dod`
- Assistant name: `dod`
- Entrypoint: `backend/app/graphs/dod_deployment_graph.py:make_graph_dod`

`langgraph.json`:

```json
{
  "dependencies": [
    "."
  ],
  "graphs": {
    "dod": "backend/app/graphs/dod_deployment_graph.py:make_graph_dod"
  },
  "image_distro": "wolfi",
  "env": ".env"
}
```

The adapter graph is intentionally small:

```text
START -> run_dod -> END
```

The `run_dod` node delegates to the existing `run_dod_agent` orchestration
service. It does not call Azure DevOps, Azure OpenAI, Cosmos DB, or ServiceNow
directly.

## Structured Input

Use structured input as the production contract. Messages-only input is not used
for production because pipeline, API, and SDK callers need stable typed fields
for build identity, correlation, metadata, and downstream audit references.

```json
{
  "organization": "ado-org",
  "project": "ado-project",
  "build_id": 123456,
  "mode": "pipeline",
  "correlation_id": "optional",
  "requested_by": "optional",
  "source": "ado-pipeline",
  "metadata": {}
}
```

Required fields:

- `organization`
- `project`
- `build_id`, which must be positive

Defaults:

- `mode` defaults to `pipeline`
- `metadata` defaults to `{}`

Allowed modes:

- `pipeline`
- `local`
- `replay`
- `api`

## Output

The graph returns the shared `DoDRunOutput` shape with these top-level fields:

```json
{
  "run_id": "dod-run-...",
  "build_id": 123456,
  "status": "completed",
  "service_now_payload": {},
  "confidence": {},
  "rule_evaluation_summary": {},
  "artifact_paths": {},
  "warnings": [],
  "errors": [],
  "result": {}
}
```

The graph output prefers summary fields and artifact references. Full artifacts
remain stored separately and are not expanded by default.

## Local Smoke Test

```powershell
python scripts/smoke_langgraph_dod_import.py
```

Expected output includes:

```text
dod graph compiled successfully
```

The smoke test only imports and compiles the graph. It does not execute a DoD
run and does not call Azure DevOps, Azure OpenAI, Cosmos DB, or ServiceNow.

## LangGraph SDK Invocation

CLI helper:

```powershell
python scripts/invoke_dod_langgraph.py `
  --organization my-ado-org `
  --project my-ado-project `
  --build-id 123456 `
  --correlation-id local-sdk-test
```

The helper reads `DOD_LANGGRAPH_URL` and optional `LANGSMITH_API_KEY`, sends
structured input to assistant `dod`, and prints only a safe summary: run id,
build id, status, rule recommended status, and artifact path keys.

```python
import os

from langgraph_sdk import get_client

client = get_client(
    url=os.environ["DOD_LANGGRAPH_URL"],
    api_key=os.environ["LANGSMITH_API_KEY"],
)

thread = await client.threads.create()

run = await client.runs.create(
    thread["thread_id"],
    "dod",
    input={
        "organization": "ado-org",
        "project": "ado-project",
        "build_id": 123456,
        "mode": "pipeline",
        "correlation_id": "local-test",
    },
)
```

Enterprise invocation should use the LangGraph SDK or LangGraph Server API.
FastAPI remains available for local and development compatibility through
`POST /api/v1/runs/generate`. CLI runs continue to use
`python scripts/run_dod_agent.py --build-id <BUILD_ID>`. All three surfaces map
through the shared DoD run contract before calling the existing orchestration
service.

## Contract Smoke Test

```powershell
python scripts/smoke_dod_contract.py
```

Expected output:

```text
dod contract smoke test passed
```

This validates contract normalization and serialization only. It does not call
Azure DevOps, Azure OpenAI, Cosmos DB, ServiceNow, LangSmith, or the deployed
LangGraph server.

## Scope Notes

- Existing Cosmos DB implementation is owned separately and should not be
  overwritten by this adapter or contract layer.
- Local Cosmos emulator support is available for developer validation only via
  `DOD_STORAGE_BACKEND=cosmos_local`.
- Enterprise deployment should use the org-owned Cosmos implementation. Do not
  overwrite org Cosmos files with the local-only adapter.
- ServiceNow writeback is out of scope for this phase.
- A2A, MCP, cron/listener automation, enterprise RBAC/auth middleware, and full
  deployment pipeline YAML are out of scope for this phase.

## Local Storage Backends

- `local_json`: existing file-backed local storage under `DATA_DIR`
- `cosmos_local`: local-only Cosmos DB emulator adapter

The local Cosmos adapter is for laptop validation only. See
`docs/local-cosmos-emulator.md`.

## Org Merge Guidance

- Merge docs, scripts, and config examples only as appropriate.
- Do not merge `backend/app/services/storage/cosmos_local_store.py` if the org
  repo already has an enterprise Cosmos implementation.
- Coordinate with the Cosmos owner before changing schema, partition key,
  database name, container name, indexing, auth, or retry behavior.
- In the org repo, map `DOD_STORAGE_BACKEND` to the org-owned Cosmos backend
  rather than using `cosmos_local` as the enterprise implementation.
