# Post-Deploy Validation

Use this order after the org LangChain/LangGraph deployment pipeline completes:

1. Confirm pipeline build, push, and deploy completed.
2. Confirm the LangGraph deployment/revision appears in the enterprise UI.
3. Call `<LANGGRAPH_API_URL>/ok`.
4. Verify graph `dod` is registered.
5. Verify the Key Vault config secret can be read by runtime.
6. Verify the LangGraph API key secret can be read by invocation scripts if
   authenticated invocation is required.
7. Verify Cosmos write path with a smoke run or real DoD run.
8. Verify `service_now_payload` artifact is persisted.
9. Verify `traceability_report` artifact is persisted.
10. Verify `rule_evaluation` artifact is persisted.
11. Verify LangSmith trace metadata appears if tracing is enabled.
12. Verify no secrets or raw payloads appear in logs/traces.
13. Verify branch environment is correct: `develop -> dev`,
    `master/release -> stg`, protected `prod`.

`/ok` proves runtime health, not full app dependency readiness. Cosmos write
validation requires an actual DoD run or explicit live dependency smoke test.

Useful commands:

```powershell
python scripts/smoke_langgraph_health.py
python scripts/smoke_langgraph_health.py --use-api-key
python scripts/smoke_keyvault_config.py
python scripts/smoke_enterprise_runtime_config.py --live-keyvault --strict
```
