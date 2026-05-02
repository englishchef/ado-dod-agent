# ado-dod-agent

Production-oriented Python service scaffold for an AI agent that will:
- collect Azure DevOps pipeline metadata,
- normalize and orchestrate processing with LangGraph,
- call an Azure-hosted model via LangChain,
- emit ServiceNow-ready summary fields.

Phase 2 adds raw Azure DevOps metadata collection with local artifact persistence.
It still does **not** implement canonical normalization, evidence buckets, LangChain prompts, LangGraph orchestration, Cosmos DB persistence, or ServiceNow writeback.

## Stack
- Python 3.12
- FastAPI
- Pydantic v2 + pydantic-settings
- httpx
- langchain
- langgraph
- azure-identity
- pytest
- ruff
- mypy

## Project Layout
```text
app/
  api/
    main.py
    routes/
      health.py
      runs.py
  core/
    config.py
    logging.py
    constants.py
  auth/
    credentials.py
    ado_token_provider.py
  clients/
    ado/
      base.py
  collectors/
  normalizers/
  prompts/
  llm/
  graph/
  scoring/
  storage/
  models/
tests/
scripts/
data/
```

## Local Setup
1. Create and activate a virtual environment.
```bash
python -m venv .venv
source .venv/bin/activate
```
On Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Create your `.env`.
```bash
cp .env.example .env
```
On Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

3. Install dependencies.
```bash
make install
```

4. Start the API.
```bash
make run
```

5. Check health endpoint.
```bash
curl http://127.0.0.1:8000/health
```

## Environment Loading
Settings are defined in `app/core/config.py` via `pydantic-settings`.
- `.env` is loaded automatically.
- Process environment variables override `.env` values.
- Data directories are created at startup under `DATA_DIR` (default: `data/`).

Key environment variables:
- App/runtime: `APP_ENV`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `DATA_DIR`
- Azure DevOps: `ADO_ORGANIZATION`, `ADO_PROJECT`, `ADO_API_VERSION` (default `7.1`)
- Entra auth: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- Future LLM integration placeholders: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`

## Phase 1 Auth (No PATs)
- Auth path uses `DefaultAzureCredential` only.
- Personal Access Tokens (PATs) are intentionally not supported.
- Your Entra identity (user, service principal, or managed identity) must be granted access in the Azure DevOps org/project.

Option A (local user auth via Azure CLI):
```bash
az login
```

Option B (service principal via environment variables):
```bash
export AZURE_TENANT_ID="<tenant-id>"
export AZURE_CLIENT_ID="<client-id>"
export AZURE_CLIENT_SECRET="<client-secret>"
```

## API Endpoints (Phase 2)
- `GET /health` returns service status and environment metadata.
- `POST /api/v1/runs/generate` remains a placeholder and points to the Phase 1 smoke script.
- `GET /api/v1/smoke/ado-auth` runs a minimal Entra token smoke ping for Azure DevOps.
- `POST /api/v1/runs/collect-raw` collects and persists raw build metadata artifacts.

## Validation and Quality Commands
```bash
make test
make lint
make format
make validate-env
make smoke-ado BUILD_ID=<BUILD_ID>
make collect-raw BUILD_ID=<BUILD_ID>
```

Direct smoke command:
```bash
python scripts/smoke_ado_auth.py --build-id <BUILD_ID>
```

Direct Phase-2 collection command:
```bash
python scripts/collect_raw_metadata.py --build-id <BUILD_ID>
```

## Phase 2 Raw Collection
Phase 2 collects read-only raw metadata for a build and saves local JSON artifacts.

What Phase 2 does:
- retrieves build metadata, timeline, work item refs, changes, optional artifacts
- hydrates work items in batch when refs are present
- attempts PR lookup from repository + commit context
- optionally collects test runs/results
- saves `raw_bundle.json` and per-collector raw files under `data/raw/{build_id}/`

What Phase 2 does not do:
- no canonical normalization
- no evidence buckets
- no LLM/prompt execution
- no LangGraph orchestration
- no ServiceNow writeback

Run sequence:
```bash
az login
make smoke-ado BUILD_ID=<BUILD_ID>
make collect-raw BUILD_ID=<BUILD_ID>
```

Expected raw folder structure:
```text
data/raw/{build_id}/
  build.json
  timeline.json
  work_item_refs.json
  work_items.json
  changes.json
  artifacts.json
  pull_requests.json
  test_runs.json
  test_results.json
  raw_bundle.json
```

Partial failures:
- Non-mandatory collector failures return `partial` status, not crash.
- Build retrieval failure returns `failed` status.
- `raw_bundle.json` always includes collector statuses and safe error summaries.

Troubleshooting:
- `401/403`: likely Azure DevOps org/project permission issue for your Entra identity.
- test APIs may require additional test read permissions.
- work item hydration may require Boards/work item read permissions.
- PR lookup may fail when a build is not associated with a pull request.
- corporate proxy/network controls may block `dev.azure.com`.
- PATs are not used by design; auth is `DefaultAzureCredential` only.

## Containerized Local Run
```bash
cp .env.example .env
docker compose up --build
```

`data/` directories are mounted and writable for local development.
