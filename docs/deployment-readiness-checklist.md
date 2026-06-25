# Deployment Readiness Checklist

## 1. Source Readiness

- `langgraph.json` exists at the repo root.
- Graph name `dod` is registered.
- `backend/app/graphs/dod_deployment_graph.py:make_graph_dod` compiles.
- `DoDRunInput` and `DoDRunOutput` contract validation passes.
- FastAPI remains importable through `backend.api.main:app`.

## 2. Dependency Readiness

- `pyproject.toml` is the authoritative dependency source.
- Runtime dependencies are installed with `python -m pip install .`.
- Container imports pass with `python scripts/smoke_container_readiness.py`.
- No local-only dependency is required for graph import or config validation.

## 3. Config Readiness

- DoD uses `/common-libs/az-langchain-agent.yml@cicd_moderndeployment` for
  build, push, and enterprise LangGraph agent deployment.
- `develop` maps to `dev`; `master` and `release` map to `stg`; `prod` is a
  protected promotion.
- The deployed LangGraph health endpoint is `/ok`.
- DoD does not need a separate Container Apps deployment path.
- `DOD_STORAGE_BACKEND` is set to `local_json` or `cosmos`.
- Cosmos config is present for deployed environments.
- Enterprise config may be supplied directly by env vars or by the
  `AGENT_CONFIG_KEY_VAULT_URL` + `AGENT_CONFIG_SECRET_NAME` JSON secret pointer.
- Process env vars override Key Vault JSON config values.
- `COSMOS_AUTH_MODE=default_credential` uses `DefaultAzureCredential` and does
  not require `COSMOS_KEY`.
- `AZURE_CREDENTIAL_MODE` is `managed_identity`, `client_secret`, or `default`.
- Enterprise deployed pods should use `AZURE_CREDENTIAL_MODE=managed_identity`.
- Dev/test service principal validation may use `AZURE_CREDENTIAL_MODE=client_secret`.
- LangSmith config is optional and failure tolerant.
- `LANGSMITH_TRACING` is canonical; `TRACING_ENABLED` is accepted as an alias.
- LangGraph platform vars are recognized but are not required for graph import.
- Secrets are provided through runtime secret/config systems, not committed files.
- `.env` and `.env.*` are excluded from Docker build context, except examples.

## 4. Storage Readiness

- `local_json` is allowed for local development.
- `cosmos` is required or strongly recommended for deployed runtime.
- Strict runtime validation rejects production-like/container `local_json`.
- Cosmos artifact documents include `document_type`.
- Partition key remains `/run_id`.

## 5. Observability Readiness

- Tracing disabled mode works.
- Tracing enabled mode works where LangSmith config and network are available.
- LangSmith failures do not fail DoD generation.
- Redaction tests pass and secrets are not traced.

## 6. Runtime Smoke

Run without external services:

```powershell
python scripts/smoke_runtime_config.py --mode local
python scripts/smoke_enterprise_runtime_config.py
python scripts/smoke_pipeline_config.py
python scripts/smoke_langgraph_health.py --help
python scripts/smoke_azure_credentials.py
python scripts/smoke_container_readiness.py
python scripts/smoke_langgraph_dod_import.py
python scripts/smoke_dod_contract.py
python scripts/smoke_langsmith_tracing.py
```

Container smoke:

```powershell
docker build -f Dockerfile -t dod-agent:phase10e .
docker run --rm dod-agent:phase10e python scripts/smoke_container_readiness.py
docker run --rm dod-agent:phase10e python scripts/smoke_runtime_config.py --mode container
```

## 7. Known Out Of Scope

- ServiceNow writeback.
- Dashboard UI or dashboard APIs.
- Metrics aggregation.
- MCP or A2A integration.
- Crons or listeners.
- Enterprise RBAC/auth middleware.
- Full pipeline YAML deployment automation.
- Container Apps deployment for DoD.
