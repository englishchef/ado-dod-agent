# LangSmith Observability

Phase 10D adds optional LangSmith tracing for the `dod` LangGraph assistant.
Tracing is centralized under `backend/app/services/observability` so business
logic does not call LangSmith directly.

## Configuration

```text
LANGSMITH_TRACING=false
LANGSMITH_PROJECT=dod-agent-local
LANGSMITH_ENDPOINT=
DOD_TRACE_MODE=summary
```

Trace modes:

- `metadata_only`: run ids, build ids, status, counts, scores, timings, and errors.
- `summary`: metadata plus short safe run summaries.
- `debug_redacted`: redacted input/result summaries for local debugging only.

Recommended defaults:

- Keep `LANGSMITH_TRACING=false` unless explicitly testing traces.
- Use `DOD_TRACE_MODE=summary` for local/dev.
- Use `DOD_TRACE_MODE=metadata_only` for production-like environments.

## What Is Traced

- `run_id`, `build_id`, organization, project, and correlation id.
- `graph_name=dod` and `assistant_name=dod`.
- Storage backend.
- Final status, rule recommended status, highest rule severity, confidence, and
  test completeness score.
- Artifact counts and phase/total durations.
- Safe error code/category when a run fails.

Major phases are timed at LangGraph node boundaries, including input
normalization, ADO metadata collection, canonical normalization, evidence
generation, LLM bucket generation, validation/repair/payload formatting, rule
evaluation, persistence, and final output serialization.

## What Is Never Traced

- `COSMOS_KEY`, Azure/OpenAI/LangSmith/API tokens, bearer tokens, PATs, secrets,
  passwords, credentials, or connection strings.
- Full environment variable dumps.
- Raw Azure DevOps payloads.
- Raw work item descriptions and full pull request comments.
- Full prompts or full LLM messages.
- Full evidence bundle content.
- Full ServiceNow payload content by default.

Secret-like fields are replaced with `[REDACTED]`. Large non-secret strings are
truncated.

## Local Validation

Disabled no-op smoke test:

```powershell
python scripts/smoke_langsmith_tracing.py
```

Optional enabled smoke test:

```powershell
set LANGSMITH_TRACING=true
set DOD_TRACE_MODE=summary
python scripts/smoke_langsmith_tracing.py --enabled
```

Remote LangSmith connectivity failures are non-fatal unless `--strict` is used.
LangSmith failures must not fail DoD generation.

## Troubleshooting Missing Traces

- Verify `LANGSMITH_TRACING=true`.
- Verify `LANGSMITH_PROJECT` is set to the expected project.
- Verify `LANGSMITH_API_KEY` is available in the local environment when sending
  traces to LangSmith.
- Check `DOD_TRACE_MODE`; `metadata_only` intentionally omits summaries.
- Confirm the run path uses the shared `run_dod_agent` orchestration boundary.

To disable tracing, set:

```powershell
set LANGSMITH_TRACING=false
```
