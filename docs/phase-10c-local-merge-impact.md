# Phase 10C-Local Merge Impact

## 1. Files Created Or Modified

- `.env.local.example`
- `backend/app/graphs/nodes.py`
- `backend/app/routers/dod_runs.py`
- `backend/app/services/collectors/raw_metadata.py`
- `backend/app/services/storage/__init__.py`
- `backend/app/services/storage/cosmos_local_store.py`
- `backend/app/services/storage/storage_factory.py`
- `backend/app/utils/config.py`
- `docker-compose.cosmos.yml`
- `docs/langgraph-deployment.md`
- `docs/local-cosmos-emulator.md`
- `docs/phase-10c-local-merge-impact.md`
- `pyproject.toml`
- `scripts/init_cosmos_local.py`
- `scripts/smoke_cosmos_local.py`
- `scripts/smoke_dod_graph_cosmos_local.py`
- `tests/unit/test_cosmos_local_scripts.py`
- `tests/unit/test_cosmos_local_store.py`
- `tests/unit/test_dod_langgraph_contract.py`
- `tests/unit/test_storage_backend_config.py`

## 2. Safe To Merge To Org Repo

Potentially safe, subject to normal review:

- `docs/local-cosmos-emulator.md`
- `docs/langgraph-deployment.md`
- `docs/phase-10c-local-merge-impact.md`
- `.env.local.example`, if the org repo wants local emulator examples
- `scripts/init_cosmos_local.py`, only if adapted to the org-owned Cosmos abstraction
- `scripts/smoke_cosmos_local.py`, only if adapted to the org-owned Cosmos abstraction
- `scripts/smoke_dod_graph_cosmos_local.py`, only if adapted to the org-owned Cosmos abstraction
- `tests/unit/test_storage_backend_config.py`, if aligned with org storage backend names

## 3. Do Not Merge Without Cosmos Owner Review

- `backend/app/services/storage/cosmos_local_store.py`
- `backend/app/services/storage/storage_factory.py` changes
- `backend/app/services/storage/__init__.py` changes
- `backend/app/graphs/nodes.py` storage selection changes
- `backend/app/routers/dod_runs.py` storage selection changes
- `backend/app/services/collectors/raw_metadata.py` storage selection changes
- `pyproject.toml` dependency change for `azure-cosmos`
- `docker-compose.cosmos.yml`
- Any partition key, container, schema, indexing, retry, or auth decisions
- Any changes to orchestration persistence behavior

## 4. Required Org Adaptation

The org repo already has a Cosmos implementation owned by another team member.
For org merge, replace or bypass `cosmos_local` with the org-owned Cosmos
storage backend. Do not overwrite org Cosmos files.

Use the local work as a pattern only:

- Keep `local_json` as the file-backed local backend.
- Map `DOD_STORAGE_BACKEND` to the org-owned Cosmos backend in the org repo.
- Coordinate with the Cosmos owner before changing database names, container
  names, partition keys, indexing, document schemas, retry behavior, or auth.
- Do not carry over emulator-key auth into production code.

Environment variables introduced:

- `DOD_STORAGE_BACKEND`
- `DOD_COSMOS_EMULATOR_ENABLED`
- `COSMOS_LOCAL_ENDPOINT`
- `COSMOS_LOCAL_DATABASE`
- `COSMOS_LOCAL_CONTAINER`
- `COSMOS_LOCAL_AUTH_MODE`
- `COSMOS_LOCAL_KEY`
- `COSMOS_LOCAL_DISABLE_TLS_VERIFY`
- `DOD_GRAPH_NAME`
- `DOD_ASSISTANT_NAME`
- `LANGSMITH_TRACING`
- `DOD_TRACE_MODE`

Local-only partition key:

- `/run_id`
- Compatibility wrappers may use `build:<build_id>` as `run_id` before the
  orchestration run id is available.

Known conflicts to check:

- Existing org Cosmos client or storage factory names
- Existing org database/container configuration names
- Existing org partition key conventions
- Existing org auth mode, especially managed identity
- Existing org artifact document schema

Rollback instructions:

- Set `DOD_STORAGE_BACKEND=local_json` or remove it from local env.
- Stop using `.env.local` for Cosmos local runs.
- Remove local-only scripts and docs if not needed.
- Revert storage selector changes if the org-owned abstraction supersedes them.
