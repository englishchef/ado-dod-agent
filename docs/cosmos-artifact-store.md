# Cosmos Artifact Store

The DoD agent supports an official Cosmos-backed artifact store for both local
emulator testing and future enterprise Azure Cosmos DB runtime.

Storage backend selection:

- `DOD_STORAGE_BACKEND=local_json`: existing file-backed storage under `DATA_DIR`
- `DOD_STORAGE_BACKEND=cosmos`: Cosmos-backed artifact storage

The old local prototype names `cosmos_local` and `COSMOS_LOCAL_*` are superseded.
They may be accepted as deprecated aliases for local migration only.

## Document Shape

```json
{
  "id": "<run_id>:<artifact_type>",
  "document_type": "artifact",
  "run_id": "<run_id>",
  "build_id": 123456,
  "artifact_type": "service_now_payload",
  "content": {},
  "schema_version": "1.0",
  "created_at": "...",
  "updated_at": "..."
}
```

Run summary documents use the same id and partition strategy, with
`document_type="run_summary"` and `artifact_type="run_summary"`:

```json
{
  "id": "<run_id>:run_summary",
  "document_type": "run_summary",
  "run_id": "<run_id>",
  "build_id": 123456,
  "artifact_type": "run_summary",
  "content": {},
  "schema_version": "1.0",
  "created_at": "...",
  "updated_at": "..."
}
```

Allowed `document_type` values:

- `artifact`
- `run_summary`
- `run_metrics` reserved for a future dashboard phase

`document_type` is present on new writes for future dashboard/query
compatibility. Reads remain backward compatible with existing documents that do
not yet contain the field. Phase 10D does not implement dashboard APIs,
dashboard UI, metrics aggregation, a metrics container, or reporting views.

Partition key:

- `/run_id`

Reason:

- One DoD run produces multiple artifacts.
- All artifacts for one run share a logical partition.
- Reads by `run_id` are direct.
- `build_id` remains queryable for build-oriented lookup.

## Artifact Types

- `raw_bundle`
- `canonical`
- `evidence_bundle`
- `llm_outputs`
- `validated_output`
- `service_now_payload`
- `confidence`
- `routing_decisions`
- `traceability_report`
- `rule_evaluation`
- `run_summary`

## Auth Modes

Local emulator:

```text
DOD_STORAGE_BACKEND=cosmos
COSMOS_AUTH_MODE=emulator_key
COSMOS_ENDPOINT=https://localhost:8081
COSMOS_DATABASE=dod_agent_local
COSMOS_CONTAINER=dod_runs
COSMOS_KEY=<local-emulator-key-only>
```

Key-based dev/test account:

```text
DOD_STORAGE_BACKEND=cosmos
COSMOS_AUTH_MODE=key
COSMOS_ENDPOINT=https://<cosmos-account>.documents.azure.com:443/
COSMOS_DATABASE=<database>
COSMOS_CONTAINER=<container>
COSMOS_KEY=<account-key>
```

Enterprise managed identity or workload identity:

```text
DOD_STORAGE_BACKEND=cosmos
COSMOS_AUTH_MODE=default_credential
COSMOS_ENDPOINT=https://<cosmos-account>.documents.azure.com:443/
COSMOS_DATABASE=<database>
COSMOS_CONTAINER=<container>
```

`COSMOS_KEY` is not required for `default_credential`. This path uses the
central Azure credential factory. Enterprise should use
`AZURE_CREDENTIAL_MODE=managed_identity`; set `AZURE_CLIENT_ID` only when the
runtime identity is user-assigned. `AZURE_USER_ASSIGNED_CLIENT_ID` remains a
backward-compatible alias, with `AZURE_CLIENT_ID` taking precedence.

## Initialize

Local emulator:

```powershell
python scripts/init_cosmos.py --local
```

Explicit database/container override:

```powershell
python scripts/init_cosmos.py --local --database dod_agent_local --container dod_runs
```

The script creates the database and container if missing, uses partition key
`/run_id`, and prints only a safe summary. It does not print `COSMOS_KEY`.

## Smoke Test

Artifact-only smoke test:

```powershell
python scripts/smoke_cosmos.py --local
```

Expected success:

```text
Cosmos artifact store smoke test passed
```

Optional full DoD run:

```powershell
python scripts/smoke_cosmos.py --local --full-run --build-id <BUILD_ID>
```

The full run requires ADO and Azure OpenAI configuration. The artifact-only
smoke test does not call ADO, Azure OpenAI, LangSmith, or ServiceNow.

## Deprecated Local Script Names

These wrappers remain for local transition:

- `python scripts/init_cosmos_local.py`
- `python scripts/smoke_cosmos_local.py`
- `python scripts/smoke_dod_graph_cosmos_local.py --build-id <BUILD_ID>`

They delegate to the official scripts.

## Troubleshooting

TLS/certificate errors:

- Trust the local Cosmos emulator certificate in Windows.
- For local emulator testing only, set `COSMOS_DISABLE_TLS_VERIFY=true`.

Connection refused:

- Verify the emulator is running.
- Verify port `8081` is listening.
- Verify `COSMOS_ENDPOINT=https://localhost:8081`.

Auth key mismatch:

- Copy the current local emulator key into `COSMOS_KEY`.
- Do not use production keys in `.env.local`.

Missing dependency:

- Install project dependencies so `azure-cosmos` is available.

Default credential failures:

- Verify managed identity, workload identity, or Azure CLI credentials are
  available to `DefaultAzureCredential`.
- Do not set `COSMOS_KEY` for `COSMOS_AUTH_MODE=default_credential`.
