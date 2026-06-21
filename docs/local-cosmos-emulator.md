# Local Cosmos Emulator

This guide is for local laptop validation of Cosmos-backed artifact persistence.
It is local-only and developer-only.

The local adapter in `backend/app/services/storage/cosmos_local_store.py` is not
the enterprise Cosmos implementation. If the org repo already has Cosmos code,
do not merge this local adapter into that repo unless the Cosmos owner explicitly
approves it.

## Purpose

Use `DOD_STORAGE_BACKEND=cosmos_local` to test artifact persistence against a
local Cosmos DB emulator while preserving the existing DoD orchestration path.

Supported local backend values:

- `local_json`: existing file-backed storage under `DATA_DIR`
- `cosmos_local`: local-only Cosmos DB emulator adapter

The local adapter stores documents with this shape:

```json
{
  "id": "<run_id>:<artifact_type>",
  "run_id": "<run_id>",
  "build_id": 123456,
  "artifact_type": "service_now_payload",
  "content": {},
  "created_at": "...",
  "updated_at": "..."
}
```

The local-only partition key is `/run_id`. The org implementation may use a
different database, container, schema, partition key, indexing policy, auth
mode, or retry behavior.

When existing file-style save methods do not yet have a true orchestration
`run_id`, the local adapter uses `build:<build_id>` as a compatibility run id.
The direct `save_artifact(...)` method stores the caller-provided `run_id`.

## Prerequisites

- Python project dependencies installed, including `azure-cosmos`
- A working install of `azure-cosmos` in the active virtual environment
- Azure Cosmos DB Emulator running locally
- Local emulator key copied into `.env.local`

Windows local development usually uses the installed Azure Cosmos DB Emulator.
Its endpoint is usually:

```text
https://localhost:8081
```

TLS/certificate issues may require trusting the emulator certificate. If your
local emulator setup requires it, set:

```text
COSMOS_LOCAL_DISABLE_TLS_VERIFY=true
```

Use that only for local emulator testing.

## Environment

Create local settings from the example:

```powershell
Copy-Item .env.local.example .env.local
```

Fill only the local emulator key:

```text
COSMOS_LOCAL_KEY=<your-local-emulator-key>
```

Do not put org secrets or production values in `.env.local`.

## Initialize

```powershell
python scripts/init_cosmos_local.py
```

The init script loads `.env.local`, creates the database/container if missing,
uses `/run_id` as the local partition key, and prints only a safe summary. It
does not call Azure DevOps, Azure OpenAI, LangSmith, or ServiceNow.

## Smoke Test

```powershell
python scripts/smoke_cosmos_local.py
```

The smoke script writes a small test artifact, reads it back, lists artifacts,
and prints:

```text
local Cosmos smoke test passed
```

It does not call Azure DevOps, Azure OpenAI, LangSmith, or ServiceNow.

## Optional Graph Smoke

Only run this when ADO, Azure OpenAI, and local Cosmos settings are available:

```powershell
python scripts/smoke_dod_graph_cosmos_local.py --build-id <BUILD_ID>
```

If required runtime config is missing, the script prints a skip message and
exits without running the graph.

## Docker Notes

`docker-compose.cosmos.yml` is provided as an optional local-only starting point
for the Linux Cosmos emulator image. Docker Desktop behavior can differ on
Windows, especially around certificates, ports, and data persistence. If Docker
emulator setup is unreliable, use the installed Windows Azure Cosmos DB Emulator
instead.

## Troubleshooting

TLS/certificate errors:

- Trust the emulator certificate in Windows.
- For local-only testing, set `COSMOS_LOCAL_DISABLE_TLS_VERIFY=true`.

Connection refused:

- Verify the emulator is running.
- Verify port `8081` is listening.
- Verify `COSMOS_LOCAL_ENDPOINT=https://localhost:8081`.

Auth key mismatch:

- Copy the current local emulator key into `.env.local`.
- Do not use Azure account keys or org secrets.

Missing dependency:

- Install project dependencies so `azure-cosmos` is available.
- If `python scripts/init_cosmos_local.py` says `azure-cosmos` is not installed,
  reinstall the project environment or install that package into the active venv.

## Org Merge Warning

Do not merge `backend/app/services/storage/cosmos_local_store.py` into the org
repo if the org repo already has an enterprise Cosmos implementation. For org
migration, keep the config/docs/script patterns as appropriate and map
`DOD_STORAGE_BACKEND` to the org-owned Cosmos backend.
