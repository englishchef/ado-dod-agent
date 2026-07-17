# LangGraph Deployment

Phase 10A exposes the existing DoD agent as a LangGraph-native assistant without
changing the FastAPI, CLI, orchestration, or storage behavior. Phase 10B hardens
the shared structured run contract used by LangGraph, FastAPI, and CLI callers.
Phase 10E prepares the same `dod` graph for containerized LangGraph-native
enterprise deployment. Phase 10E.5 adds the org enterprise runtime config
pattern: direct environment variables first, optional Key Vault JSON config
second, and local `.env` behavior only for development fallback.

## Confirmed Org Deployment Path

DoD uses the org LangChain/LangGraph agent deployment template:

```text
/common-libs/az-langchain-agent.yml@cicd_moderndeployment
```

The template builds the image, pushes the image, and deploys or updates the
enterprise LangGraph agent. It uses `langgraph.json` to identify graph `dod` and
its entrypoint. A separate Container Apps deployment path is not required for
DoD and should not be added unless a future dashboard/backend API is introduced.

The deployed LangGraph health endpoint is:

```text
/ok
```

`/ok` is usually an unauthenticated platform health check. If an environment
requires API-key authentication for health or invocation scripts, store the key
as a separate Key Vault string secret referenced by
`LANGGRAPH_KEY_VAULT_URL` and `LANGGRAPH_KEY_VAULT_SECRET_NAME`. Do not place
the actual LangGraph API key inside the DoD agent runtime config JSON.

Branch strategy:

- `develop` deploys to `dev`.
- `master` and `release` deploy to `stg`.
- `prod` is a protected promotion after `stg`.

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

Phase 10D adds optional LangSmith trace metadata through the shared
observability helper. Trace metadata uses `graph_name=dod` and
`assistant_name=dod`, includes the configured storage backend, and can be
disabled without affecting DoD runs.

## Required Deployment Files

- `langgraph.json`
- `pyproject.toml`
- `backend/app/graphs/dod_deployment_graph.py`
- `backend/app/models/dod_contracts.py`
- `backend/app/services/orchestration/dod_run_service.py`
- `backend/app/services/storage/*`
- `backend/app/services/observability/*`
- `backend/api/main.py` when FastAPI is deployed in the same image

`pyproject.toml` is the authoritative dependency declaration. There is no
runtime `requirements.txt` in this repo. The Docker image installs the package
from `pyproject.toml` and includes `langgraph.json` in the working directory.

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

## LangGraph state versus artifact storage

LangGraph state is a compact orchestration contract. It carries run identity,
status, the current phase, small summaries, ServiceNow/confidence output, and
artifact references. Full Azure DevOps raw bundles, canonical documents,
evidence bundles, recursive timeline derivation, LLM output, validation output,
traceability reports, rule evaluations, routing bundles, and run summaries
belong in `ArtifactStore`.

A node that needs a full document loads it from `ArtifactStore`, processes it,
persists the next document, and returns only a reference plus a bounded summary:

```json
{
  "bucket_3_summary": {
    "selected_environment": "UAT",
    "selected_stage_name": "UAT",
    "estimated_backout_minutes": 90,
    "normalized_actions": ["solution_upgrade"],
    "fallback_used": false
  },
  "artifact_paths": {
    "canonical": "cosmos://<run-id>/canonical",
    "evidence_bundle": "cosmos://<run-id>/evidence_bundle",
    "bucket_3_rollback_risk": "cosmos://<run-id>/bucket_3_rollback_risk"
  }
}
```

The Bucket 3 artifact retains detailed `backout_step_derivation` evidence,
including recursive descendant/source/ignored-task details. Traversal queues,
visited sets, parent-child indexes, raw logs, SDK objects, and that detailed
derivation are not graph-state fields. This changes checkpoint shape only; it
does not change recursive traversal or Bucket 3 selection and backout rules.

All node updates must be plain dictionaries containing strict JSON-compatible
values. Datetimes, UUIDs, Pydantic models, dataclasses, enums, and paths must be
normalized before they enter state. Clients, credentials, responses,
generators, coroutines, exception instances, and arbitrary custom classes are
rejected. Diagnostics report only key paths, Python types, serialized sizes,
and the largest state keys; they never print values or raw artifacts.

Application-level state guards are configurable independently of platform
limits:

```text
DOD_GRAPH_STATE_WARN_BYTES=262144
DOD_GRAPH_STATE_MAX_BYTES=1048576
```

The warning threshold records `GRAPH_STATE_SIZE_WARNING`. The hard limit and
unsupported values fail with compact `GRAPH_STATE_TOO_LARGE`,
`GRAPH_STATE_NOT_JSON_SERIALIZABLE`, or `GRAPH_STATE_UNSUPPORTED_TYPE` errors
before the node update is returned for checkpointing. These defaults are
safeguards, not documented enterprise platform limits.

The enterprise LangGraph PostgreSQL/PGCosmos checkpoint store is separate from
the DoD Cosmos artifact container. A `PGCosmosError` can be a platform
persistence failure and is not automatically proof of invalid application
state. First check the safe state-shape/size diagnostics. If state is JSON-safe
and within the configured hard limit, platform checkpoint retry remains owned
by the enterprise LangGraph runtime; the application does not add retries that
could duplicate artifacts or repeat LLM calls.

## Local Smoke Test

```powershell
python scripts/smoke_langgraph_dod_import.py
python scripts/smoke_graph_state_serialization.py
```

Expected output includes:

```text
dod graph compiled successfully
```

These smoke tests import and compile the graph and validate representative
compact state. They do not execute a DoD run and do not call Azure DevOps,
Azure OpenAI, Cosmos DB, enterprise LangGraph, LangSmith, Key Vault, or
ServiceNow.

Container readiness smoke test:

```powershell
python scripts/smoke_container_readiness.py
```

Runtime config smoke test:

```powershell
python scripts/smoke_runtime_config.py --mode local
python scripts/smoke_runtime_config.py --mode container --strict
python scripts/smoke_enterprise_runtime_config.py
python scripts/smoke_pipeline_config.py
python scripts/smoke_langgraph_health.py --help
```

The runtime config smoke test validates settings only. It does not call Azure
DevOps, Azure OpenAI, Cosmos DB, LangSmith, or ServiceNow.

## LangGraph SDK Invocation

CLI helper:

```powershell
python scripts/invoke_dod_langgraph.py `
  --organization my-ado-org `
  --project my-ado-project `
  --build-id 123456 `
  --correlation-id local-sdk-test
```

The helper reads `LANGGRAPH_API_URL` or `DOD_LANGGRAPH_URL`. If configured, it
retrieves the LangGraph API key from
`LANGGRAPH_KEY_VAULT_URL` + `LANGGRAPH_KEY_VAULT_SECRET_NAME` using the
centralized Azure credential factory. It sends structured input to assistant
`dod` and prints only a safe summary: run id, build id, status, pipeline action,
rule recommended status, and artifact path keys.

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

- The `dod` graph uses the storage backend selected by configuration.
- Local JSON and Cosmos artifact storage are supported.
- Enterprise deployment should use `DOD_STORAGE_BACKEND=cosmos`.
- Enterprise auth should prefer `COSMOS_AUTH_MODE=default_credential`.
- `LANGGRAPH_ASSISTANT_ID` defaults to `dod`; platform LangGraph variables are
  recognized but not required for graph import.
- Local Cosmos emulator runs use `COSMOS_AUTH_MODE=emulator_key`.
- ServiceNow writeback is out of scope for this phase.
- Container Apps deployment is out of scope for DoD in this phase.
- A2A, MCP, cron/listener automation, enterprise RBAC/auth middleware, and full
  deployment pipeline YAML are out of scope for this phase.

## Local Storage Backends

- `local_json`: existing file-backed local storage under `DATA_DIR`
- `cosmos`: Cosmos-backed artifact store

Local development may use `local_json`. Container, enterprise, and
production-like runtimes should use `DOD_STORAGE_BACKEND=cosmos`; strict runtime
config validation fails when production-like/container mode uses `local_json`.

See `docs/cosmos-artifact-store.md`.

Cosmos config for deployed runtime:

```text
DOD_STORAGE_BACKEND=cosmos
COSMOS_AUTH_MODE=default_credential
COSMOS_ENDPOINT=https://<cosmos-account>.documents.azure.com:443/
COSMOS_DATABASE=<database>
COSMOS_CONTAINER=<container>
```

The same values may come from the agent Key Vault JSON secret pointed to by
`AGENT_CONFIG_KEY_VAULT_URL` and `AGENT_CONFIG_SECRET_NAME`. Direct process env
vars override Key Vault JSON values.

Local emulator config:

```text
DOD_STORAGE_BACKEND=cosmos
COSMOS_AUTH_MODE=emulator_key
COSMOS_ENDPOINT=https://localhost:8081
COSMOS_DATABASE=dod_agent_local
COSMOS_CONTAINER=dod_runs
COSMOS_KEY=<local-emulator-key-only>
```

## Observability

LangSmith tracing is disabled by default:

```text
LANGSMITH_TRACING=false
DOD_TRACE_MODE=summary
LANGSMITH_PROJECT=dod-agent-local
```

When enabled, traces include small safe metadata and timing summaries. Raw Azure
DevOps payloads, full evidence bundles, full prompts, full LLM messages,
secrets, and full ServiceNow payload values are not traced by default. LangSmith
package/config/connectivity failures are treated as no-op failures and must not
fail DoD generation.

See `docs/langsmith-observability.md`.

## Container Build Smoke

Build with the repo Dockerfile:

```powershell
docker build -f Dockerfile -t dod-agent:phase10e .
```

Run import/config checks inside the image:

```powershell
docker run --rm dod-agent:phase10e python scripts/smoke_container_readiness.py
docker run --rm dod-agent:phase10e python scripts/smoke_runtime_config.py --mode container
```

PowerShell helper:

```powershell
.\scripts\smoke_docker_build.ps1
```

These smoke checks do not require secrets.

## Troubleshooting

Graph import failure:

- Run `python scripts/smoke_container_readiness.py`.
- Verify `langgraph.json` contains graph name `dod`.
- Verify the entrypoint is
  `backend/app/graphs/dod_deployment_graph.py:make_graph_dod`.

Missing dependency:

- Install from `pyproject.toml` with `python -m pip install .`.
- Rebuild the Docker image after dependency changes.

Wrong working directory:

- Run smoke scripts from the repo root or container `/workspace`.
- Verify `langgraph.json` exists in the current directory.

Environment file not loaded:

- LangGraph-native deployment should provide environment variables through the
  platform secret/config system.
- The Docker image does not copy `.env`.

Cosmos config missing:

- Run `python scripts/smoke_runtime_config.py --storage-backend cosmos`.
- For `COSMOS_AUTH_MODE=emulator_key` or `key`, `COSMOS_KEY` is required.
- For `COSMOS_AUTH_MODE=default_credential`, `COSMOS_KEY` is not required.

LangSmith disabled/enabled behavior:

- `LANGSMITH_TRACING=false` requires no LangSmith API key.
- `LANGSMITH_TRACING=true` validates configuration and remains failure tolerant
  at runtime.

## Cosmos Guidance

- Coordinate with the Cosmos owner before changing schema, partition key,
  database name, container name, indexing, auth, or retry behavior.
- The official DoD artifact document partition key is `/run_id`.
- Graph nodes, FastAPI routers, rule engine, validators, and prompt code should
  not call Cosmos directly.
