# ado-dod-agent

Python backend for collecting Azure DevOps pipeline/build metadata and preparing future DoD summarization workflows.

Phase 2 scope:
- Azure DevOps Entra auth via `DefaultAzureCredential`
- build smoke validation
- raw metadata collection
- local JSON artifact persistence under `data/raw/{build_id}/`

Out of scope in Phase 2:
- normalization/evidence buckets
- LangChain/LangGraph execution
- Cosmos DB
- ServiceNow writeback

## Backend Layout
```text
backend/
  api/
    main.py
  app/
    routers/
      dod_runs.py
      health.py
      smoke.py
    services/
      auth/
      ado/
      collectors/
      storage/
    models/
      inputs.py
      raw.py
      outputs.py
    utils/
      config.py
      logging.py
      constants.py
scripts/
tests/
  unit/
  integration/
data/
```

## Setup
1. Create venv and activate.
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Create `.env`.
```powershell
Copy-Item .env.example .env
```

3. Install deps.
```powershell
python -m pip install -e ".[dev]"
```

4. Run API.
```powershell
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Auth (No PATs)
Use `DefaultAzureCredential` only.

Option A (recommended local):
```powershell
az login
```

Option B (service principal env vars):
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

Your Entra identity must have access to the target ADO org/project.

## Key Env Vars
- `APP_ENV`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`
- `ADO_ORGANIZATION`, `ADO_PROJECT`, `ADO_API_VERSION` (default `7.1`)
- `DATA_DIR` (default `data`)
- optional: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- optional future: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`

## Endpoints
- `GET /health`
- `GET /api/v1/smoke/ado-auth`
- `POST /api/v1/runs/generate` (placeholder)
- `POST /api/v1/runs/collect-raw`

## Commands
```powershell
python scripts/validate_env.py
python scripts/smoke_ado_auth.py --build-id <BUILD_ID>
python scripts/collect_raw_metadata.py --build-id <BUILD_ID>
pytest
ruff check .
mypy backend scripts tests
```

If `make` is installed:
```powershell
make run
make test
make lint
make smoke-ado BUILD_ID=<BUILD_ID>
make collect-raw BUILD_ID=<BUILD_ID>
```

## Raw Output
Expected files (depending on permissions/data availability):
- `data/raw/{build_id}/build.json`
- `data/raw/{build_id}/timeline.json`
- `data/raw/{build_id}/work_item_refs.json`
- `data/raw/{build_id}/changes.json`
- `data/raw/{build_id}/raw_bundle.json`
- optional: `artifacts.json`, `work_items.json`, `pull_requests.json`, `test_runs.json`, `test_results.json`

Partial failures:
- optional collectors can fail and return `partial`
- mandatory build retrieval failure returns `failed`

Troubleshooting:
- `401/403`: likely ADO permission issue
- test/work item APIs may need extra read permissions
- PR lookup may not apply for non-PR builds
- corporate proxy/network can block `dev.azure.com`
