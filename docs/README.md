# ado-dod-agent

Python backend for collecting Azure DevOps build metadata and preparing Definition-of-Done outputs.

## Current Phase Scope
- Phase 1: Entra auth + ADO smoke validation (`DefaultAzureCredential` only, no PATs)
- Phase 2: raw metadata collection to local artifacts
- Phase 3: deterministic canonical normalization from raw bundle to canonical JSON

Out of scope:
- evidence buckets (Phase 4)
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
      normalizers/
      storage/
      llm/
      scoring/
    models/
      inputs.py
      outputs.py
      raw.py
      canonical.py
    graphs/
    prompts/
    utils/
scripts/
tests/
  unit/
  integration/
data/
  raw/
  normalized/
  evidence/
  output/
```

## Setup
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Run API:
```powershell
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## Auth
Use `DefaultAzureCredential` only.

Option A (recommended):
```powershell
az login
```

Option B:
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

No PATs are used.

## Endpoints
- `GET /health`
- `GET /api/v1/smoke/ado-auth`
- `POST /api/v1/runs/generate` (placeholder)
- `POST /api/v1/runs/collect-raw`
- `POST /api/v1/runs/normalize`

## Phase 2 Raw Collection
Input:
- build id + org/project context

Output:
- `data/raw/{build_id}/raw_bundle.json`
- related raw collector artifacts

CLI:
```powershell
python scripts/collect_raw_metadata.py --build-id <BUILD_ID>
```

Make:
```powershell
make collect-raw BUILD_ID=<BUILD_ID>
```

## Phase 3 Canonical Normalization
Phase 3 reads existing raw metadata only. It does not call ADO or LLMs.

Input file:
- `data/raw/{build_id}/raw_bundle.json`

Output file:
- `data/normalized/{build_id}/canonical.json`

CLI:
```powershell
python scripts/normalize_raw_metadata.py --build-id <BUILD_ID>
```
Optional explicit raw bundle path:
```powershell
python scripts/normalize_raw_metadata.py --build-id <BUILD_ID> --raw-bundle data/raw/<BUILD_ID>/raw_bundle.json
```

Make:
```powershell
make normalize-raw BUILD_ID=<BUILD_ID>
```

Normalize API:
- `POST /api/v1/runs/normalize`
- request: `build_id` required, `raw_bundle_path` optional
- returns safe summary + canonical artifact path

Canonical document includes:
- `run_context`
- `change_context`
- `execution_context`
- `quality_context`
- `risk_context`
- `normalization_metadata`

Partial raw data is supported. Missing optional sections are represented with explicit `missing_*` lists and metadata warnings.

## Commands
```powershell
python scripts/validate_env.py
python scripts/smoke_ado_auth.py --build-id <BUILD_ID>
python scripts/collect_raw_metadata.py --build-id <BUILD_ID>
python scripts/normalize_raw_metadata.py --build-id <BUILD_ID>
python -m pytest -q
python -m ruff check .
python -m mypy --no-incremental --cache-dir .cache/mypy_backend backend scripts tests
```

If `make` is installed:
```powershell
make run
make test
make lint
make smoke-ado BUILD_ID=<BUILD_ID>
make collect-raw BUILD_ID=<BUILD_ID>
make normalize-raw BUILD_ID=<BUILD_ID>
```

## Troubleshooting
- `401/403`: usually ADO permission issue for your Entra identity.
- Missing tests/work-items/PRs can be permission or data-shape dependent and may produce partial outputs.
- Corporate proxy/network controls may block `dev.azure.com`.
