# ado-dod-agent

Python backend for collecting Azure DevOps build metadata and preparing Definition-of-Done outputs.

## Current Phase Scope
- Phase 1: Entra auth + ADO smoke validation (`DefaultAzureCredential` only, no PATs)
- Phase 2: raw metadata collection to local artifacts
- Phase 3: deterministic canonical normalization from raw bundle to canonical JSON
- Phase 4: deterministic evidence bucket generation from canonical JSON
- Phase 5A: local Foundry/Azure OpenAI keyless model access smoke validation
- Phase 5B: ServiceNow field draft generation from evidence buckets
- Phase 6: validation, confidence scoring, and ServiceNow-ready payload assembly

Out of scope:
- ServiceNow writeback
- LangGraph orchestration
- Cosmos DB

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
py -3.11 -m venv .venv
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
- `POST /api/v1/runs/build-evidence`

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

## Phase 4 Evidence Buckets
Phase 4 reads canonical metadata only. It does not call ADO or LLMs.

Input file:
- `data/normalized/{build_id}/canonical.json`

Output files:
- `data/evidence/{build_id}/bucket_1_change_intent.json`
- `data/evidence/{build_id}/bucket_2_execution_validation.json`
- `data/evidence/{build_id}/bucket_3_rollback_risk.json`
- `data/evidence/{build_id}/evidence_bundle.json`

CLI:
```powershell
python scripts/build_evidence_buckets.py --build-id <BUILD_ID>
```
Optional explicit canonical path:
```powershell
python scripts/build_evidence_buckets.py --build-id <BUILD_ID> --canonical data/normalized/<BUILD_ID>/canonical.json
```

Make:
```powershell
make build-evidence BUILD_ID=<BUILD_ID>
```

Evidence API:
- `POST /api/v1/runs/build-evidence`
- request: `build_id` required, `canonical_path` optional, `max_items_per_section` optional
- returns safe summary + evidence artifact paths

Phase 4 scope:
- deterministic evidence selection only
- no LLM calls yet
- prompt-driven generation starts in Phase 5

## Phase 5A LLM Access Smoke Validation
Phase 5A validates the local Azure AI Foundry / Azure OpenAI-compatible model endpoint access path before any ServiceNow field generation is implemented. It uses Microsoft Entra ID through `DefaultAzureCredential` and RBAC/PIM. No API key is used or supported.

Required configuration:
```powershell
AZURE_OPENAI_ENDPOINT=https://<resource-name>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
AZURE_OPENAI_API_VERSION=<api-version-from-portal>
AZURE_OPENAI_AUTH_MODE=entra
LLM_TEMPERATURE=0
LLM_MAX_TOKENS=1000
LLM_TIMEOUT_SECONDS=60
```

Required Azure access:
- PIM role activated before running the smoke script.
- Model invoke RBAC role assigned, such as Cognitive Services OpenAI User or equivalent Foundry role.
- User authenticated through Azure CLI or another `DefaultAzureCredential` source in the current shell/dev container.
- Correct subscription and tenant selected.

CLI:
```powershell
python scripts/smoke_llm_access.py
```

Make:
```powershell
make smoke-llm
```

Expected successful response:
```json
{"status":"ok"}
```

Troubleshooting:
- `401`: token audience or authentication problem.
- `403`: RBAC, PIM, or assignment scope problem.
- `DeploymentNotFound`: deployment name and endpoint do not match.
- `DefaultAzureCredential` failure: no usable credential in the current environment.

Phase 5A does not generate ServiceNow fields. Full LLM generation from evidence buckets is Phase 5B.

## Phase 5B ServiceNow Field Draft Generation
Phase 5B generates draft ServiceNow Definition of Done field text from the three deterministic evidence buckets created in Phase 4. Phase 5A model smoke access must succeed first.

Required input:
- `data/evidence/{build_id}/evidence_bundle.json`

Outputs:
- `data/output/{build_id}/bucket_1_output.json`
- `data/output/{build_id}/bucket_2_output.json`
- `data/output/{build_id}/bucket_3_output.json`
- `data/output/{build_id}/llm_outputs.json`

Generated target fields:
- `change_description`
- `short_change_description`
- `justification`
- `testing_performed`
- `implementation_plan`
- `validation_plan`
- `backout_plan`
- `risk_impact_analysis`

CLI:
```powershell
python scripts/generate_service_now_fields.py --build-id <BUILD_ID>
```

Make:
```powershell
make generate-fields BUILD_ID=<BUILD_ID>
```

Optional explicit inputs:
```powershell
python scripts/generate_service_now_fields.py --build-id <BUILD_ID> --evidence-bundle data/evidence/<BUILD_ID>/evidence_bundle.json
python scripts/generate_service_now_fields.py --build-id <BUILD_ID> --bucket-1 data/evidence/<BUILD_ID>/bucket_1_change_intent.json --bucket-2 data/evidence/<BUILD_ID>/bucket_2_execution_validation.json --bucket-3 data/evidence/<BUILD_ID>/bucket_3_rollback_risk.json
```

Phase 5B reminders:
- No ServiceNow update/writeback occurs.
- No repair retry logic is implemented yet.
- No deterministic confidence scoring is implemented yet.
- Generated output is draft text and should be reviewed.
- Missing PR, test, rollback, or other evidence should be reflected honestly in `missing_information` and conservative field language.

## Phase 6 Validate And Assemble Output
Phase 6 validates the Phase 5B LLM outputs, flags unsupported claims, computes deterministic confidence, and assembles the final flat ServiceNow-ready payload. It does not update ServiceNow.

Inputs:
- `data/output/{build_id}/llm_outputs.json`
- `data/evidence/{build_id}/evidence_bundle.json`

Outputs:
- `data/output/{build_id}/validated_output.json`
- `data/output/{build_id}/service_now_payload.json`
- `data/output/{build_id}/confidence.json`

CLI:
```powershell
python scripts/validate_service_now_payload.py --build-id <BUILD_ID>
```

Make:
```powershell
make validate-output BUILD_ID=<BUILD_ID>
```

Validation behavior:
- Errors fail validation and produce a non-zero script exit code.
- Warnings do not fail validation.
- Missing test evidence lowers confidence but does not automatically fail.
- Missing PR evidence is not a hard failure.
- Unsupported claims such as unproven test-pass, rollback-tested, or absolute no-risk claims are flagged.
- No ServiceNow update/writeback occurs in this phase.
- LangGraph orchestration starts in a later phase.

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
python scripts/build_evidence_buckets.py --build-id <BUILD_ID>
python scripts/smoke_llm_access.py
python scripts/generate_service_now_fields.py --build-id <BUILD_ID>
python scripts/validate_service_now_payload.py --build-id <BUILD_ID>
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
make build-evidence BUILD_ID=<BUILD_ID>
make smoke-llm
make generate-fields BUILD_ID=<BUILD_ID>
make validate-output BUILD_ID=<BUILD_ID>
```

## Troubleshooting
- `401/403`: usually ADO permission issue for your Entra identity.
- Missing tests/work-items/PRs can be permission or data-shape dependent and may produce partial outputs.
- Corporate proxy/network controls may block `dev.azure.com`.
