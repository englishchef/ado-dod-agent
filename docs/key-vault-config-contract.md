# Key Vault Config Contract

`AGENT_CONFIG_SECRET_NAME` points to the primary DoD app runtime configuration
JSON. The secret stores runtime configuration only. It must be a JSON object and
must not contain generated artifacts, raw Azure DevOps payloads, or full output
payloads.

## Sample Secret

Use placeholders in repo examples. Do not commit real secret values.

The org uses a two-secret model:

1. Agent runtime config JSON secret, referenced by `AGENT_CONFIG_SECRET_NAME`.
2. LangGraph API key string secret, referenced by `LANGGRAPH_KEY_VAULT_SECRET_NAME`.

Do not store the actual LangGraph API key in the agent runtime config JSON.

```json
{
  "AZURE_CREDENTIAL_MODE": "managed_identity",
  "DOD_STORAGE_BACKEND": "cosmos",
  "COSMOS_AUTH_MODE": "default_credential",
  "COSMOS_ENDPOINT": "https://<cosmos-account>.documents.azure.com:443/",
  "COSMOS_DATABASE": "<database>",
  "COSMOS_CONTAINER": "<container>",
  "ADO_ORGANIZATION": "<ado-org>",
  "AZURE_OPENAI_ENDPOINT": "https://<openai-resource>.openai.azure.com/",
  "AZURE_OPENAI_DEPLOYMENT": "<deployment>",
  "LANGSMITH_PROJECT": "dod-agent-dev"
}
```

Enterprise deployed pod example:

```json
{
  "AZURE_CREDENTIAL_MODE": "managed_identity",
  "AZURE_CLIENT_ID": "<user-assigned-managed-identity-client-id-if-required>",
  "DOD_STORAGE_BACKEND": "cosmos",
  "COSMOS_AUTH_MODE": "default_credential",
  "COSMOS_ENDPOINT": "https://<cosmos-account>.documents.azure.com:443/",
  "COSMOS_DATABASE": "<database>",
  "COSMOS_CONTAINER": "<container>"
}
```

Dev testing with client secret example:

```json
{
  "AZURE_CREDENTIAL_MODE": "client_secret",
  "AZURE_CLIENT_ID": "<app-registration-client-id>",
  "AZURE_TENANT_ID": "<tenant-id>",
  "AZURE_CLIENT_SECRET": "<client-secret>",
  "DOD_STORAGE_BACKEND": "cosmos",
  "COSMOS_AUTH_MODE": "default_credential",
  "COSMOS_ENDPOINT": "https://<cosmos-account>.documents.azure.com:443/",
  "COSMOS_DATABASE": "<database>",
  "COSMOS_CONTAINER": "<container>"
}
```

Local laptop example:

```json
{
  "AZURE_CREDENTIAL_MODE": "default",
  "DOD_STORAGE_BACKEND": "cosmos",
  "COSMOS_AUTH_MODE": "default_credential",
  "COSMOS_ENDPOINT": "https://<cosmos-account>.documents.azure.com:443/",
  "COSMOS_DATABASE": "<database>",
  "COSMOS_CONTAINER": "<container>"
}
```

## Required Keys

- `DOD_STORAGE_BACKEND`
- `COSMOS_AUTH_MODE`
- `COSMOS_ENDPOINT`
- `COSMOS_DATABASE`
- `COSMOS_CONTAINER`
- `ADO_ORGANIZATION`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `LANGSMITH_PROJECT`

## Optional Keys

- `ADO_PROJECT`
- `AZURE_CREDENTIAL_MODE`
- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_SECRET`, only for approved `client_secret` dev/test scenarios
- `AZURE_USER_ASSIGNED_CLIENT_ID`, backward-compatible alias for user-assigned
  managed identity client id
- `DOD_TRACE_MODE`
- `LANGSMITH_TRACING`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_AUTH_MODE`
- `ADO_AUTH_MODE`
- `LANGSMITH_ENDPOINT`
- `LANGSMITH_TLS_VERIFY`
- `LANGSMITH_CA_BUNDLE`

Enterprise deployments should prefer:

```text
COSMOS_AUTH_MODE=default_credential
```

Do not include `COSMOS_KEY` for `default_credential`.

`COSMOS_KEY` should not be stored unless explicitly using `key` auth in a
non-production test setup. Generated artifacts and raw ADO payloads should never
be stored in Key Vault. LangGraph API keys should remain in the dedicated
LangGraph Key Vault secret pattern if the org uses
`LANGGRAPH_KEY_VAULT_SECRET_NAME`.

The LangGraph API key secret should contain only:

```text
<actual-langgraph-api-key-value>
```

It is used by external invocation scripts and wrappers, not by the `dod` graph
runtime itself.

Security notes:

- Do not commit `AZURE_CLIENT_SECRET`.
- Prefer `managed_identity` in enterprise.
- Use `client_secret` only for approved dev/test scenarios.
- Do not print credential values.
- The pipeline identity and runtime identity may be different.
- Successful deployment does not prove runtime has Cosmos write permission.
- Validate with a real write/read smoke test after deployment.

## Never Store

- Generated artifacts.
- Raw Azure DevOps payloads.
- Full evidence bundles.
- ServiceNow generated payloads.
- LLM prompts or messages.
- Access tokens, API keys, or client secrets unless a later phase explicitly
  changes the contract.

## Rotation And Changes

1. Update the Key Vault secret with the new JSON object.
2. Keep key names stable where possible.
3. Run `python scripts/smoke_keyvault_config.py` from an identity with access.
4. Run `python scripts/smoke_enterprise_runtime_config.py --live-keyvault --strict`
   when live validation is intended.
5. Restart or redeploy the runtime if the platform does not refresh secrets in
   place.

Smoke scripts print only key counts or key names when requested. They never
print values.
