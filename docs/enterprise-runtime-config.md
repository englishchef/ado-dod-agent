# Enterprise Runtime Config

Phase 10E.5 aligns the DoD agent with the org LangChain/LangGraph runtime
configuration pattern while keeping local tests offline.

## Runtime Model

The org pipeline injects deployment environment variables from
`.pipelines/config/<env>/vars.yml`. The agent can also load an agent-specific
JSON config secret from Azure Key Vault when both variables are present:

```text
AGENT_CONFIG_KEY_VAULT_URL=https://<vault-name>.vault.azure.net/
AGENT_CONFIG_SECRET_NAME=<secret-name>
```

Config precedence is deterministic:

1. Explicit process environment variables.
2. Key Vault JSON config values for missing keys.
3. Existing `.env` local development behavior.
4. Code defaults.

Key Vault values never overwrite already-set process environment variables.
Secret values and full JSON config are not printed by smoke scripts.

## Confirmed Deployment Model

The DoD agent uses the org LangChain/LangGraph agent deployment path:

```text
/common-libs/az-langchain-agent.yml@cicd_moderndeployment
```

Confirmed platform behavior:

- Builds the image.
- Pushes the image.
- Deploys or updates the enterprise LangGraph agent.
- Uses `langgraph.json` to identify graph `dod` and its entrypoint.
- Does not require a separate Container Apps deployment for DoD.
- Exposes deployed runtime health at `/ok`.

Branch strategy:

- `develop` deploys to `dev`.
- `master` and `release` deploy to `stg`.
- `prod` is a protected promotion after `stg`.

DoD deployment is LangGraph-platform only for now. DoD should not use the
Container Apps deployment pipeline unless a future dashboard/backend API is
added.

## Azure Credential

Key Vault, Cosmos `default_credential` auth, Azure OpenAI/Foundry Entra auth,
and future Azure SDK integrations use the centralized Azure credential factory.

Supported modes:

- `AZURE_CREDENTIAL_MODE=managed_identity`: enterprise deployed LangGraph pods.
- `AZURE_CREDENTIAL_MODE=client_secret`: approved dev/test service principal.
- `AZURE_CREDENTIAL_MODE=default`: local laptop, Azure CLI, and default Azure
  SDK chain.

If `AZURE_CREDENTIAL_MODE` is absent, `default` is used for local compatibility.

In `managed_identity` mode, `AZURE_CLIENT_ID` means the user-assigned managed
identity client id. If `AZURE_CLIENT_ID` is absent,
`AZURE_USER_ASSIGNED_CLIENT_ID` is accepted as a backward-compatible alias. If
both are set, `AZURE_CLIENT_ID` wins. If neither is set, system-assigned managed
identity is used.

In `client_secret` mode, `AZURE_CLIENT_ID` means the app registration client id,
and these values are required:

```text
AZURE_CREDENTIAL_MODE=client_secret
AZURE_CLIENT_ID=<app-registration-client-id>
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_SECRET=<client-secret>
```

In `default` mode, `AZURE_CLIENT_ID` is optional and may be used as a managed
identity client id when running in Azure. Without it, plain
`DefaultAzureCredential` is used.

Local developer testing can continue to use Azure CLI credentials.

## Runtime Identity And Permissions

The deployed LangGraph workload obtains Azure access through the identity
available inside the enterprise runtime. App code uses `DefaultAzureCredential`;
the effective identity must have access to dependencies at runtime.

Required access at a high level:

- Key Vault secret read permission for `AGENT_CONFIG_SECRET_NAME`.
- Cosmos DB data-plane read/write/query/upsert permission for the DoD
  database/container.
- Azure OpenAI/Foundry access if model calls use Entra auth.
- ADO access per the org-approved approach.

pipeline permissions and runtime permissions are not the same thing. Successful
image build/push does not prove Cosmos write permission. A successful
/ok health check does not prove Cosmos write permission. Cosmos write must be
validated by a smoke run or real DoD run.

## Key Vault JSON

The Key Vault secret must be a JSON object. See
`docs/key-vault-config-contract.md` for the full contract.

Enterprise Cosmos config should use:

```text
DOD_STORAGE_BACKEND=cosmos
COSMOS_AUTH_MODE=default_credential
COSMOS_ENDPOINT=https://<cosmos-account>.documents.azure.com:443/
COSMOS_DATABASE=<database>
COSMOS_CONTAINER=<container>
```

`COSMOS_KEY` is not required for `default_credential`. Local emulator and
key-based modes still require `COSMOS_KEY`.

## LangGraph API Key Secret

The LangGraph API key is for external callers and scripts that invoke the
deployed LangGraph API. It is not required for the `dod` graph to import,
compile, or execute inside the deployed runtime.

Keep these Key Vault concerns separate:

- `AGENT_CONFIG_KEY_VAULT_URL` + `AGENT_CONFIG_SECRET_NAME`: JSON object with
  DoD runtime config such as Cosmos, Azure OpenAI/Foundry, ADO, and tracing.
- `LANGGRAPH_KEY_VAULT_URL` + `LANGGRAPH_KEY_VAULT_SECRET_NAME`: secret value is
  only the actual LangGraph API key string.

LangGraph API invocation config:

```text
LANGGRAPH_API_URL=https://<deployed-langgraph-url>
LANGGRAPH_ASSISTANT_ID=dod
LANGGRAPH_API_KEY_HEADER=x-api-key
LANGGRAPH_KEY_VAULT_URL=https://<vault-name>.vault.azure.net/
LANGGRAPH_KEY_VAULT_SECRET_NAME=<langgraph-api-key-secret-name>
```

Retrieval uses the centralized Azure credential factory. Never print or log the
API key. `/ok` may not require the API key, but authenticated invocation likely
does.

## LangSmith

Tracing remains optional and failure tolerant. The app accepts both names:

```text
LANGSMITH_TRACING=true
TRACING_ENABLED=true
```

`LANGSMITH_TRACING` wins when both are set. `TRACING_ENABLED` is a
backward-compatible alias only when `LANGSMITH_TRACING` is absent.

Supported LangSmith config keys:

- `LANGSMITH_PROJECT`
- `LANGSMITH_ENDPOINT`
- `LANGSMITH_TLS_VERIFY`
- `LANGSMITH_CA_BUNDLE`

No LangSmith config is required when tracing is disabled.

## LangGraph Platform Variables

The org platform may inject:

- `LANGGRAPH_API_URL`
- `LANGGRAPH_ASSISTANT_ID`
- `LANGGRAPH_API_KEY_HEADER`
- `LANGGRAPH_KEY_VAULT_URL`
- `LANGGRAPH_KEY_VAULT_SECRET_NAME`

These are recognized by runtime validation but are not required for graph import
or graph compilation. `LANGGRAPH_ASSISTANT_ID` defaults to `dod`.

## Local Development

Local development may continue to use:

```text
DOD_STORAGE_BACKEND=local_json
```

Default pytest and offline smoke tests do not call Azure Key Vault, Cosmos,
LangSmith, Azure DevOps, Azure OpenAI, ServiceNow, or PIM.

Offline enterprise smoke:

```powershell
python scripts/smoke_enterprise_runtime_config.py
python scripts/smoke_enterprise_runtime_config.py --mock-keyvault-json tmp/dod-agent-config.sample.json --strict
python scripts/smoke_pipeline_config.py
python scripts/smoke_langgraph_health.py --help
python scripts/smoke_azure_credentials.py
```

Live Key Vault smoke, only when access is available:

```powershell
$env:AGENT_CONFIG_KEY_VAULT_URL="https://<vault-name>.vault.azure.net/"
$env:AGENT_CONFIG_SECRET_NAME="<secret-name>"
python scripts/smoke_keyvault_config.py
python scripts/smoke_langgraph_health.py
python scripts/smoke_langgraph_health.py --use-api-key
```

## Troubleshooting

Key Vault access denied:

- Verify the runtime identity has `get` permission for secrets.
- Verify `AZURE_USER_ASSIGNED_CLIENT_ID` matches the assigned identity when used.

Secret not found:

- Verify `AGENT_CONFIG_SECRET_NAME`.
- Verify the value is in the vault from `AGENT_CONFIG_KEY_VAULT_URL`.

Invalid JSON:

- The secret value must be a JSON object, not an array, string, or comments.

Cosmos auth failure:

- For enterprise, prefer `COSMOS_AUTH_MODE=default_credential`.
- Verify Cosmos RBAC for the runtime identity.
- Do not set `COSMOS_KEY` for `default_credential`.

Missing env var:

- Check `.pipelines/config/<env>/vars.yml` and the Key Vault JSON secret.
- Remember process env values override Key Vault JSON values.

LangSmith alias mismatch:

- Prefer `LANGSMITH_TRACING`.
- If both `LANGSMITH_TRACING` and `TRACING_ENABLED` are set, the canonical
  `LANGSMITH_TRACING` value wins.
