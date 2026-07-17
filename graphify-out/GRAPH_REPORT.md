# Graph Report - ado-dod-agent  (2026-07-17)

## Corpus Check
- 261 files · ~94,836 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2621 nodes · 6781 edges · 127 communities (113 shown, 14 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 192 edges (avg confidence: 0.61)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `87526141`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- builder.py
- AzureDevOpsBaseClient
- config.py
- Settings
- raw_metadata.py
- dod_runs.py
- collect_raw_metadata
- smoke_ado_auth.py
- dod_contracts.py
- FakeStore
- DodGraphState
- test_bucket_prompts.py
- get_azure_credential
- output_repair.py
- RuleResult
- nodes.py
- select_prompt_strategy
- test_evidence_builder.py
- CosmosArtifactStore
- dod_deployment_graph.py
- canonical.py
- CombinedLlmOutputs
- langsmith_tracing.py
- LocalJsonStore
- load_agent_config_from_key_vault
- DodRunSummary
- output_validator.py
- service.py
- extract_json_object
- validate_bucket_3_fields
- evaluate_rules.py
- canonical.py
- render_workflow_ascii.py
- get_langgraph_api_key
- run_dod_workflow
- smoke_enterprise_runtime_config.py
- AzureFoundryChatClient
- Any
- validate_pipeline_config
- score_confidence
- servicenow_formatter.py
- redaction.py
- assess_risk_tier
- invoke_dod_langgraph.py
- test_completeness.py
- assess_evidence_quality
- smoke_cosmos.py
- validate_service_now_payload.py
- clean_servicenow_field_text
- _required_cosmos_config
- .save_output_json
- test_output_validator.py
- README.md
- smoke_container_readiness.py
- smoke_llm_access.py
- normalize_raw_metadata.py
- normalize_raw_bundle
- run_dod_agent
- cosmos_artifact_store.py
- test_llm_generator.py
- generator.py
- evaluate_risk_rules
- generate_service_now_fields.py
- bucket_3_selection.py
- evaluate_unsupported_claim_rules
- azure_foundry_client.py
- LangGraph Deployment
- run_dod_agent.py
- smoke_langgraph_health.py
- test_dod_graph_advanced_nodes.py
- evaluate_backout_rules
- build_evidence_buckets.py
- evaluate_rules
- ArtifactStore
- test_change_intent_field_separation.py
- Enterprise Runtime Config
- init_cosmos.py
- test_dod_runs_artifact_api.py
- Any
- .load_artifact
- test_cosmos_document_type.py
- ._get_container
- .output_path
- smoke_azure_credentials.py
- smoke_keyvault_config.py
- test_field_quality_rules.py
- test_test_completeness_rules.py
- test_validate_service_now_payload_script.py
- test_validated_output_models.py
- get_storage_store
- Cosmos Artifact Store
- Deployment Readiness Checklist
- build_key_vault_headers
- make_decision
- smoke_keyvault_config.py
- .settings_customise_sources
- .get_pull_request
- Key Vault Config Contract
- LangSmith Observability
- langgraph.json
- test_dod_runs_rule_evaluation_api.py
- _required_cosmos_config
- .get_test_results
- resolve_runtime_config
- DoD Run Contract
- test_dockerignore_rules.py
- test_runtime_identity_docs_contract.py
- normalized_words
- test_normalize_endpoint_returns_expected_summary
- AGENTS.md
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- post-deploy-validation.md
- __init__.py
- conftest.py
- ado-dod-agent

## God Nodes (most connected - your core abstractions)
1. `Settings` - 183 edges
2. `LocalJsonStore` - 93 edges
3. `get_settings()` - 66 edges
4. `CosmosArtifactStore` - 65 edges
5. `build_evidence_bundle()` - 38 edges
6. `_complete_canonical()` - 37 edges
7. `DodGraphState` - 35 edges
8. `collect_raw_metadata()` - 35 edges
9. `validate_bucket_3_fields()` - 35 edges
10. `LlmClientError` - 33 edges

## Surprising Connections (you probably didn't know these)
- `main()` --indirect_call--> `AzureCredentialConfigError`  [INFERRED]
  scripts/smoke_azure_credentials.py → backend/app/core/azure_credentials.py
- `main()` --indirect_call--> `EnterpriseConfigError`  [INFERRED]
  scripts/smoke_enterprise_runtime_config.py → backend/app/core/enterprise_config.py
- `test_make_graph_dod_imports_and_compiles()` --calls--> `make_graph_dod()`  [EXTRACTED]
  tests/unit/test_dod_langgraph_entrypoint.py → backend/app/graphs/dod_deployment_graph.py
- `test_validate_input_node_fails_when_build_id_missing()` --calls--> `validate_input_node()`  [EXTRACTED]
  tests/unit/test_dod_graph_state.py → backend/app/graphs/nodes.py
- `test_validate_input_node_initializes_run_state()` --calls--> `validate_input_node()`  [EXTRACTED]
  tests/unit/test_dod_graph_state.py → backend/app/graphs/nodes.py

## Import Cycles
- None detected.

## Communities (127 total, 14 thin omitted)

### Community 0 - "builder.py"
Cohesion: 0.10
Nodes (24): DoDRunInput, normalize_dod_run_input(), Validate and normalize structured DoD run input., Structured input contract for FastAPI, CLI, and LangGraph invocation., DodRunSummary, BaseModel, Phase 7A orchestration run summary models., Structured non-sensitive issue captured during orchestration. (+16 more)

### Community 1 - "AzureDevOpsBaseClient"
Cohesion: 0.06
Nodes (36): AsyncClient, AzureDevOpsBaseClient, AzureDevOpsClientConfig, AzureDevOpsClientError, Any, Exception, Response, Execute an authenticated GET request and return a JSON object. (+28 more)

### Community 2 - "config.py"
Cohesion: 0.05
Nodes (50): AccessToken, Smoke validation endpoints., Build client config from application settings., AzureDevOpsTokenProvider, AzureIdentityAdoTokenProvider, Azure DevOps token provider implementations., Token provider backed by Azure Identity for Entra-authenticated ADO calls., Return bearer-token headers for synchronous call sites. (+42 more)

### Community 3 - "Settings"
Cohesion: 0.10
Nodes (38): Return safe validation errors/warnings for the optional Key Vault pointer., validate_agent_config_pointer(), _build_parser(), build_settings(), _configured(), _is_present(), _is_production_like(), _langsmith_tracing_enabled() (+30 more)

### Community 4 - "raw_metadata.py"
Cohesion: 0.15
Nodes (30): Models package exports., BuildEvidenceResponse, HealthResponse, NormalizeRawResponse, BaseModel, Output schemas returned by API endpoints., Service liveness payload., Placeholder run generation response for Phase 0. (+22 more)

### Community 5 - "dod_runs.py"
Cohesion: 0.08
Nodes (50): ApiIssue, ArtifactResponse, GenerateRunRequest, GenerateRunResponse, BaseModel, API request/response models for Phase 8 pipeline-facing endpoints., Request body for running the DoD agent workflow., API-safe issue model. (+42 more)

### Community 6 - "collect_raw_metadata"
Cohesion: 0.13
Nodes (23): BuildEvidenceInput, CollectRawInput, BaseModel, Input schemas for API operations., Phase-2 request model for raw metadata collection., Phase-4 request model for deterministic evidence bucket generation., collect_raw(), Collect raw build metadata and persist local artifacts. (+15 more)

### Community 7 - "smoke_ado_auth.py"
Cohesion: 0.08
Nodes (25): correlation_id_middleware(), lifespan(), Response, FastAPI entrypoint for ado-dod-agent., Initialize runtime resources at startup., Attach a correlation id to logs and responses for each request., ensure_data_directories(), Runtime configuration loaded from environment variables. (+17 more)

### Community 8 - "dod_contracts.py"
Cohesion: 0.14
Nodes (26): _derive_rule_evaluation_summary(), _dict_or_empty(), DoDRuleEvaluationSummary, DoDRunArtifactPaths, DoDRunError, DoDRunWarning, _int_or_default(), _list_of_dicts() (+18 more)

### Community 9 - "FakeStore"
Cohesion: 0.11
Nodes (19): _base_state(), _fake_llm_outputs(), _fake_validated(), FakeModel, FakeStore, Any, MonkeyPatch, Path (+11 more)

### Community 10 - "DodGraphState"
Cohesion: 0.12
Nodes (39): LangGraph workflow package., build_evidence_buckets_node(), evaluate_rules_node(), generate_llm_outputs_node(), _generate_llm_outputs_once(), _load_evidence_bundle_from_state(), _merge_artifact_paths(), _model_or_none() (+31 more)

### Community 11 - "test_bucket_prompts.py"
Cohesion: 0.07
Nodes (38): build_prompt(), Any, Prompt builder for Phase 5B change intent fields., Build the bucket 1 prompt from deterministic evidence only., _strategy_guidance(), build_prompt(), Any, Prompt builder for Phase 5B execution and validation fields. (+30 more)

### Community 12 - "get_azure_credential"
Cohesion: 0.10
Nodes (36): AzureCredentialConfigError, get_azure_credential(), get_azure_credential_mode(), get_redacted_credential_summary(), _managed_identity_client_id(), _present(), _present_value(), Any (+28 more)

### Community 13 - "output_repair.py"
Cohesion: 0.13
Nodes (40): format_backout_minutes(), Format rounded minutes without seconds or false precision., _backout_steps_for_actions(), _best_lower_environment_stage_duration(), _brief_backout_mitigation(), bucket_3_claim_evidence_text(), bucket_3_evidence(), _build_backout_plan() (+32 more)

### Community 14 - "RuleResult"
Cohesion: 0.12
Nodes (34): ConfidenceAdjustment, BaseModel, Deterministic rule evaluation models for Phase 9., Base config for rule evaluation payloads., RuleBaseModel, RuleEvaluation, RuleEvaluationSummary, RuleResult (+26 more)

### Community 15 - "nodes.py"
Cohesion: 0.16
Nodes (30): assemble_run_result_node(), _coerce_build_id(), _coerce_float(), _coerce_str(), collect_raw_metadata_node(), _collector_issue(), _duration_ms(), _extract_paths() (+22 more)

### Community 16 - "select_prompt_strategy"
Cohesion: 0.15
Nodes (26): EvidenceQualityAssessment, BaseModel, Deterministic routing models for Phase 7B orchestration., Quality assessment for prompt-ready evidence buckets., Risk tier assessment derived from deterministic evidence., Persisted routing audit artifact., RiskTierAssessment, RoutingDecisionBundle (+18 more)

### Community 17 - "test_evidence_builder.py"
Cohesion: 0.14
Nodes (41): CanonicalArtifact, CanonicalJob, CanonicalPullRequest, CanonicalStage, CanonicalTask, CanonicalWorkItem, build_evidence_bundle(), _container_activity_items() (+33 more)

### Community 18 - "CosmosArtifactStore"
Cohesion: 0.14
Nodes (9): _content_from_document(), CosmosArtifactStore, Any, List artifact types stored for a run id., Load run summary by run id or by build id for endpoint compatibility., Cosmos-backed artifact store for local emulator and enterprise runtime., Create the configured database and container if missing., Load one artifact by run id and artifact type. (+1 more)

### Community 19 - "dod_deployment_graph.py"
Cohesion: 0.09
Nodes (27): make_graph_dod(), Any, LangGraph deployment adapter for the DoD agent., Compile the enterprise LangGraph deployment graph for the DoD assistant., _run_dod_node(), DoDGraphState, normalize_dod_input(), TypedDict (+19 more)

### Community 20 - "canonical.py"
Cohesion: 0.24
Nodes (32): CanonicalTestResult, CanonicalTestRun, _as_dict(), _as_float(), _as_int(), _as_list(), _as_str(), _contains_any() (+24 more)

### Community 21 - "CombinedLlmOutputs"
Cohesion: 0.13
Nodes (27): Bucket1GeneratedOutput, Bucket2GeneratedOutput, Bucket3GeneratedOutput, CombinedLlmOutputs, LlmModelMetadata, LlmOutputBaseModel, BaseModel, Pydantic models for Phase 5B generated ServiceNow field drafts. (+19 more)

### Community 22 - "langsmith_tracing.py"
Cohesion: 0.11
Nodes (32): Observability helpers for DoD agent tracing., build_run_metadata(), _duration_ms(), get_trace_mode(), is_tracing_enabled(), _langsmith_client(), _phase_durations(), _project_name() (+24 more)

### Community 23 - "LocalJsonStore"
Cohesion: 0.11
Nodes (24): Path, Tests for local JSON storage abstraction., Store should load Phase 4 evidence bundle and bucket helpers., Store should support Phase 6 output helpers., Store should save/load UTF-8 JSON under DATA_DIR., Store should support Phase 7A run summary helpers., Store should support Phase 7B routing decisions helpers., Store should ensure run dirs and build canonical raw path. (+16 more)

### Community 24 - "load_agent_config_from_key_vault"
Cohesion: 0.15
Nodes (24): create_default_azure_credential(), EnterpriseConfigError, load_agent_config_from_key_vault(), parse_agent_config_json(), _present_value(), Any, ValueError, Enterprise runtime config resolution for the DoD agent. (+16 more)

### Community 25 - "DodRunSummary"
Cohesion: 0.36
Nodes (14): Any, MonkeyPatch, Tests for Phase 8 /api/v1/runs/generate endpoint., _request(), _summary(), test_generate_endpoint_accepts_x_correlation_id_header(), test_generate_endpoint_body_correlation_id_overrides_header(), test_generate_endpoint_calls_run_dod_agent() (+6 more)

### Community 26 - "output_validator.py"
Cohesion: 0.20
Nodes (30): ValidationIssue, display_application_name(), normalize_application_candidate(), Normalize candidate identity for deterministic comparison and deduplication., Return one business-readable application or service display name., _as_dict(), _backout_derivation_issues(), _bucket() (+22 more)

### Community 27 - "service.py"
Cohesion: 0.11
Nodes (28): BucketValidationResult, BaseModel, Validated Phase 6 ServiceNow-ready output models., Base config for validated output payloads., ServiceNowPayload, ValidatedOutputBaseModel, format_service_now_payload(), Return a clean ServiceNow payload with exactly the eight supported fields. (+20 more)

### Community 28 - "extract_json_object"
Cohesion: 0.20
Nodes (14): _candidate_json_strings(), _extract_balanced_object(), extract_json_object(), JsonParseError, Any, Defensive JSON object extraction for LLM responses., Raised when an LLM response cannot be parsed as one JSON object., Extract and parse a JSON object from raw LLM text. (+6 more)

### Community 29 - "validate_bucket_3_fields"
Cohesion: 0.18
Nodes (38): Normalize Bucket 3 fields to concise, evidence-grounded ServiceNow text., repair_bucket_3_fields(), Validate concise, evidence-grounded backout and risk field intent., _risk_impact_sentences(), validate_bucket_3_fields(), _assert_narrative_risk_format(), _evidence(), _labeled_risk_text() (+30 more)

### Community 30 - "evaluate_rules.py"
Cohesion: 0.13
Nodes (28): _build_parser(), build_summary(), format_summary(), _load_optional(), _load_required(), main(), Any, ArgumentParser (+20 more)

### Community 31 - "canonical.py"
Cohesion: 0.23
Nodes (26): CanonicalBaseModel, CanonicalCommit, CanonicalDodDocument, CanonicalScanSummary, CanonicalTestSummary, ChangeContext, ExecutionContext, NormalizationMetadata (+18 more)

### Community 32 - "render_workflow_ascii.py"
Cohesion: 0.16
Nodes (27): build_ascii_from_workflow(), _build_parser(), _conditional_edges_by_source(), _continue_target(), _display_node(), _edge_with_label(), GraphEdge, _linear_chain() (+19 more)

### Community 33 - "get_langgraph_api_key"
Cohesion: 0.13
Nodes (23): Validate key names and required enterprise config shape without values., validate_key_vault_config_contract(), _build_parser(), build_settings_from_sources(), load_mock_key_vault_config(), main(), Any, ArgumentParser (+15 more)

### Community 34 - "run_dod_workflow"
Cohesion: 0.24
Nodes (26): Any, Run the Phase 7A workflow and return final graph state., run_dod_workflow(), _input(), _patch_common(), Any, MonkeyPatch, Tests for Phase 7B advanced workflow routing. (+18 more)

### Community 35 - "smoke_enterprise_runtime_config.py"
Cohesion: 0.19
Nodes (11): Application readiness response., ReadyResponse, health(), _is_configured(), Depends, JSONResponse, Health-check endpoint., Return service health and runtime metadata. (+3 more)

### Community 36 - "AzureFoundryChatClient"
Cohesion: 0.19
Nodes (20): AzureFoundryChatClient, LlmClientError, Raised when local LLM smoke validation cannot be completed safely., Small Entra-only wrapper around LangChain AzureChatOpenAI., DummyModel, DummyResponse, Any, Exception (+12 more)

### Community 37 - "Any"
Cohesion: 0.05
Nodes (40): LocalJsonStore, _make_json_safe(), Any, Path, Load one artifact by build id using local output filenames., List artifact types referenced by a local run summary., Save run summary through the shared ArtifactStore contract., Recursively convert values into JSON-serializable equivalents. (+32 more)

### Community 38 - "validate_pipeline_config"
Cohesion: 0.16
Nodes (24): _build_parser(), _contains_container_apps_reference(), main(), PipelineConfigValidation, ArgumentParser, Path, Static validation for the DoD enterprise pipeline configuration., Safe static validation result for the .pipelines folder. (+16 more)

### Community 39 - "score_confidence"
Cohesion: 0.20
Nodes (23): _adjust(), _as_dict(), _bucket(), _clamp(), _deterministic_bucket_score(), _has_acceptance_or_business_value(), _model_confidence(), Any (+15 more)

### Community 40 - "servicenow_formatter.py"
Cohesion: 0.18
Nodes (22): FieldTraceability, BaseModel, Traceability report models for ServiceNow payload generation., Base config for traceability payloads., TraceabilityBaseModel, TraceabilityReport, build_traceability_report(), _dict_list() (+14 more)

### Community 41 - "redaction.py"
Cohesion: 0.19
Nodes (21): _first_error_value(), _is_raw_content_key(), _is_secret_key(), _normalize_key(), _overall_confidence(), Any, Safe redaction and trace-summary helpers for DoD observability., Return a redacted copy of a dictionary. (+13 more)

### Community 42 - "assess_risk_tier"
Cohesion: 0.22
Nodes (21): _as_dict(), _as_int(), _as_list(), _as_str(), assess_risk_tier(), _bool_dict(), _collect_missing_context(), _dedupe() (+13 more)

### Community 43 - "invoke_dod_langgraph.py"
Cohesion: 0.12
Nodes (21): _build_parser(), build_structured_input(), format_safe_summary(), invoke_dod_assistant(), main(), Any, ArgumentParser, Namespace (+13 more)

### Community 44 - "test_completeness.py"
Cohesion: 0.27
Nodes (22): _all_text(), _bucket(), calculate_test_completeness_score(), evaluate_test_completeness_rules(), has_artifact_evidence(), _has_failed_signal(), has_failed_tests(), has_security_scan_signals() (+14 more)

### Community 45 - "assess_evidence_quality"
Cohesion: 0.22
Nodes (20): _as_dict(), _as_int(), _as_list(), _as_str(), _assess_bucket_1(), _assess_bucket_2(), _assess_bucket_3(), assess_evidence_quality() (+12 more)

### Community 46 - "smoke_cosmos.py"
Cohesion: 0.16
Nodes (17): _build_parser(), load_env_local(), Deprecated wrapper for local Cosmos artifact smoke testing., main(), _missing_full_run_config(), ArgumentParser, Path, Smoke-test the configured Cosmos artifact store. (+9 more)

### Community 47 - "validate_service_now_payload.py"
Cohesion: 0.14
Nodes (28): ValidatedDodOutput, _build_parser(), build_summary(), format_summary(), _load_evidence_bundle(), _load_llm_outputs(), main(), persist_outputs() (+20 more)

### Community 48 - "clean_servicenow_field_text"
Cohesion: 0.16
Nodes (19): clean_servicenow_field_text(), normalize_servicenow_whitespace(), Clean one ServiceNow field without changing business meaning., Remove raw/internal reference tokens from field text., Normalize whitespace while preserving meaningful numbered lists., Remove markdown code fences from generated text., _remove_field_label(), remove_markdown_artifacts() (+11 more)

### Community 49 - "_required_cosmos_config"
Cohesion: 0.27
Nodes (7): FakeContainer, Any, Tests for the official Cosmos artifact store without an emulator., _settings(), test_cosmos_config_default_credential_does_not_require_key(), test_cosmos_config_requires_key_for_key_modes(), test_save_load_and_list_with_mocked_container()

### Community 50 - ".save_output_json"
Cohesion: 0.23
Nodes (18): normalize_raw_bundle(), Normalize a Phase-2 raw bundle into canonical deterministic structure., _build_complete_raw_bundle(), _bundle_with_message(), Any, Tests for deterministic canonical normalizer., test_complete_raw_bundle_normalizes_successfully(), test_missing_tests_does_not_fail() (+10 more)

### Community 51 - "test_output_validator.py"
Cohesion: 0.22
Nodes (17): detect_raw_reference_leakage(), Return whether text contains raw/internal evidence references., evidence_bundle(), _issues(), Tests for deterministic Phase 6 output validation., test_absolute_no_risk_claim_is_flagged(), test_clean_payload_passes_leakage_validation(), test_detect_raw_reference_leakage_returns_true_for_raw_paths() (+9 more)

### Community 52 - "README.md"
Cohesion: 0.10
Nodes (19): Auth, Backend Layout, Backout Plan, Commands, Current Phase Scope, Endpoints, Phase 2 Raw Collection, Phase 3 Canonical Normalization (+11 more)

### Community 53 - "smoke_container_readiness.py"
Cohesion: 0.16
Nodes (19): DoDRunOutput, Structured output contract for DoD agent run summaries., graph_entrypoint(), load_langgraph_config(), main(), Any, Path, Smoke-check container readiness for LangGraph-native DoD deployment. (+11 more)

### Community 54 - "smoke_llm_access.py"
Cohesion: 0.10
Nodes (25): get_settings(), Return cached application settings., endpoint_host(), format_success_summary(), _is_azure_auth_failure(), _is_azure_http_failure(), main(), Exception (+17 more)

### Community 55 - "normalize_raw_metadata.py"
Cohesion: 0.17
Nodes (11): ChatModel, _extract_content_part(), _is_placeholder(), _parse_json_object(), Any, Protocol, Azure OpenAI-compatible Foundry chat client using Entra ID auth., Minimal protocol for LangChain chat models used by this wrapper. (+3 more)

### Community 56 - "normalize_raw_bundle"
Cohesion: 0.67
Nodes (3): MonkeyPatch, Endpoint should return safe summary with output artifact paths., test_build_evidence_endpoint_returns_expected_summary()

### Community 57 - "run_dod_agent"
Cohesion: 0.16
Nodes (16): _parse_datetime(), Any, datetime, Service entry point for Phase 7A DoD agent orchestration., Run the DoD agent workflow and return the persisted run summary model., run_dod_agent(), Phase 7A orchestration service package., RuntimeError (+8 more)

### Community 58 - "cosmos_artifact_store.py"
Cohesion: 0.13
Nodes (12): _artifact_from_relative_path(), _artifact_type_from_filename(), _cosmos_uri(), _document_type_for_artifact(), _make_json_safe(), Path, Official Cosmos DB artifact store for DoD run artifacts., Save a run summary artifact. (+4 more)

### Community 59 - "test_llm_generator.py"
Cohesion: 0.29
Nodes (16): _bucket_1_response(), _bucket_2_response(), _bucket_3_response(), DummyClient, _evidence_bundle(), Any, MonkeyPatch, Tests for Phase 5B LLM generator service. (+8 more)

### Community 60 - "generator.py"
Cohesion: 0.21
Nodes (18): PromptStrategySelection, Selected prompt strategies for each bucket., generate_all_buckets(), _generate_bucket(), generate_bucket_1(), generate_bucket_2(), generate_bucket_3(), _generate_bucket_with_retry() (+10 more)

### Community 61 - "evaluate_risk_rules"
Cohesion: 0.23
Nodes (16): evaluate_risk_rules(), _mentions(), _overall_confidence(), Any, Risk and impact consistency rules., Evaluate risk and impact consistency rules., _risk_flags(), _risk_tier() (+8 more)

### Community 62 - "generate_service_now_fields.py"
Cohesion: 0.20
Nodes (17): _build_parser(), build_summary(), format_summary(), _load_evidence_inputs(), main(), persist_outputs(), Any, ArgumentParser (+9 more)

### Community 63 - "bucket_3_selection.py"
Cohesion: 0.05
Nodes (110): ApplicationCandidateScoreEvidence, ApplicationResolutionEvidence, ArtifactEvidence, BackoutTimeDerivationEvidence, ChangeIntentEvidence, CommitEvidence, EvidenceBaseModel, EvidenceBundle (+102 more)

### Community 64 - "evaluate_unsupported_claim_rules"
Cohesion: 0.24
Nodes (15): _approval_supported(), _contains_any(), evaluate_unsupported_claim_rules(), _field_text(), Any, Rules for unsupported claims in generated ServiceNow field text., Evaluate unsupported AI-generated claim rules., _rollback_supported() (+7 more)

### Community 65 - "azure_foundry_client.py"
Cohesion: 0.20
Nodes (13): _build_parser(), format_result_summary(), main(), _parse_bool(), Any, ArgumentParser, Namespace, CLI entrypoint for Phase-2 raw metadata collection. (+5 more)

### Community 66 - "LangGraph Deployment"
Cohesion: 0.12
Nodes (15): Confirmed Org Deployment Path, Container Build Smoke, Contract Smoke Test, Cosmos Guidance, Graph Registration, LangGraph Deployment, LangGraph SDK Invocation, Local Smoke Test (+7 more)

### Community 67 - "run_dod_agent.py"
Cohesion: 0.16
Nodes (22): _build_parser(), _evidence_quality_summary(), format_summary(), _load_routing_payload(), main(), _overall_confidence(), _prompt_strategy_summary(), Any (+14 more)

### Community 68 - "smoke_langgraph_health.py"
Cohesion: 0.07
Nodes (47): get_langgraph_api_key(), get_langgraph_api_key_config(), get_redacted_langgraph_api_key_summary(), LangGraphApiKeyConfig, LangGraphApiKeyConfigError, _present_value(), Any, ValueError (+39 more)

### Community 69 - "test_dod_graph_advanced_nodes.py"
Cohesion: 0.18
Nodes (18): assess_evidence_quality_node(), assess_risk_tier_node(), Assess evidence quality for downstream routing., Assess risk tier for downstream prompt strategy and final routing., _severity_for_quality(), _evidence_bundle(), _FakeModel, Any (+10 more)

### Community 70 - "evaluate_backout_rules"
Cohesion: 0.25
Nodes (12): evaluate_backout_rules(), Any, Backout plan quality rules., Evaluate backout plan quality rules., _risk_flags(), _rollback_supported(), _rule(), Tests for backout plan quality rules. (+4 more)

### Community 71 - "build_evidence_buckets.py"
Cohesion: 0.20
Nodes (13): _build_parser(), format_summary(), main(), Any, ArgumentParser, Namespace, CLI entrypoint for Phase-4 deterministic evidence bucket generation., Render a compact and safe CLI summary. (+5 more)

### Community 72 - "evaluate_rules"
Cohesion: 0.36
Nodes (12): evaluate_rules(), Any, Evaluate deterministic post-generation rules against existing artifacts., _clean_payload(), Tests for Phase 9 rule engine orchestration., _strong_evidence(), test_recommended_status_completed_when_no_rules(), test_recommended_status_completed_with_warnings() (+4 more)

### Community 73 - "ArtifactStore"
Cohesion: 0.22
Nodes (5): ArtifactStore, Any, Path, Protocol, Storage contract shared by local JSON and Cosmos artifact stores.

### Community 74 - "test_change_intent_field_separation.py"
Cohesion: 0.15
Nodes (16): detect_delivery_detail_leakage(), Return whether a change-intent field exposes delivery-only metadata., Conservatively repair delivery leakage and repeated description sentences., _remove_delivery_detail_sentences(), repair_change_intent_fields(), _restore_terminal_punctuation(), _strip_trailing_delivery_clause(), _evidence_bundle() (+8 more)

### Community 75 - "Enterprise Runtime Config"
Cohesion: 0.17
Nodes (11): Azure Credential, Confirmed Deployment Model, Enterprise Runtime Config, Key Vault JSON, LangGraph API Key Secret, LangGraph Platform Variables, LangSmith, Local Development (+3 more)

### Community 76 - "init_cosmos.py"
Cohesion: 0.23
Nodes (10): _build_parser(), load_env_local(), Deprecated wrapper for local Cosmos initialization., main(), ArgumentParser, Namespace, Path, Initialize the configured Cosmos artifact store database/container. (+2 more)

### Community 77 - "test_dod_runs_artifact_api.py"
Cohesion: 0.08
Nodes (34): Depends, Perform a minimal Azure DevOps Entra auth smoke check., smoke_ado_auth(), Path, Return all data directories used by the pipeline lifecycle., Return official Cosmos auth mode, honoring deprecated local aliases., Return official Cosmos endpoint, honoring deprecated local aliases., Return official Cosmos key, honoring deprecated local aliases. (+26 more)

### Community 78 - "Any"
Cohesion: 0.08
Nodes (35): GenerateRunInput, Phase-0 placeholder payload for generate-run orchestration., CollectorError, Safe, structured collector error detail., AzureDevOpsBuildClient, Any, Azure DevOps build API client., Read-only build endpoints for smoke validation and future collectors. (+27 more)

### Community 79 - ".load_artifact"
Cohesion: 0.20
Nodes (5): Return canonical local path for a Phase R3 traceability report., Return canonical local path for a Phase 9 rule evaluation artifact., Return canonical local path for a Phase 7A run summary., Return canonical local path for a Phase 7B routing decisions artifact., Return canonical local path for a generated output artifact file.

### Community 80 - "test_cosmos_document_type.py"
Cohesion: 0.31
Nodes (7): FakeContainer, Any, Tests for Cosmos document_type compatibility fields., _settings(), test_cosmos_artifact_write_includes_artifact_document_type(), test_cosmos_read_remains_compatible_when_document_type_missing(), test_cosmos_run_summary_write_includes_run_summary_document_type()

### Community 81 - "._get_container"
Cohesion: 0.40
Nodes (3): Delete one smoke-test artifact if it exists., Return the stable Cosmos document id for an artifact., test_cosmos_document_id_and_partition_key()

### Community 82 - ".output_path"
Cohesion: 0.17
Nodes (14): _build_parser(), format_summary(), main(), Any, ArgumentParser, Namespace, CLI entrypoint for Phase-3 canonical normalization., Render a safe, compact summary for console output. (+6 more)

### Community 83 - "smoke_azure_credentials.py"
Cohesion: 0.22
Nodes (13): normalize_field_aliases(), Extract one JSON object from raw text without evaluating code., Normalize common field aliases without changing business content., Repair structural fields required by Phase 5B output models., repair_json_text(), repair_llm_output_shape(), Tests for deterministic Phase 6 output repair., test_normalize_alias_risk_and_impact_analysis() (+5 more)

### Community 85 - "test_field_quality_rules.py"
Cohesion: 0.47
Nodes (9): _ids(), _payload(), Tests for ServiceNow field quality rules., test_duplicate_content_triggers_rule(), test_empty_field_triggers_rule(), test_generic_validation_plan_triggers_rule(), test_long_short_description_triggers_rule(), test_markdown_triggers_rule() (+1 more)

### Community 86 - "test_test_completeness_rules.py"
Cohesion: 0.42
Nodes (9): _empty_evidence(), Tests for Phase 9 test completeness scoring and rules., _rules(), test_failed_tests_trigger_rule(), test_missing_nonfunctional_evidence_triggers_rule(), test_no_test_evidence_triggers_no_automated_results(), test_score_is_low_when_no_test_or_validation_evidence_exists(), test_score_is_medium_when_tests_missing_but_validation_exists() (+1 more)

### Community 87 - "test_validate_service_now_payload_script.py"
Cohesion: 0.29
Nodes (8): _build_parser(), main(), ArgumentParser, Validate Azure credential configuration without live Azure calls by default., Any, Tests for the Azure credential smoke script., test_smoke_azure_credentials_default_does_not_call_network(), test_smoke_azure_credentials_help_works_without_azure_access()

### Community 88 - "test_validated_output_models.py"
Cohesion: 0.39
Nodes (8): ConfidenceScore, Tests for Phase 6 validated output models., test_confidence_score_rejects_out_of_range(), test_service_now_payload_rejects_empty_field(), test_service_now_payload_rejects_placeholder(), test_service_now_payload_validates_all_8_fields(), test_validated_dod_output_serializes(), valid_payload()

### Community 89 - "get_storage_store"
Cohesion: 0.17
Nodes (12): Local JSON storage abstraction for raw metadata artifacts., get_storage_store(), Storage backend selection for DoD artifacts., Return the configured artifact store., Any, Tests for the common artifact store contract., test_local_json_store_satisfies_artifact_store_contract(), Path (+4 more)

### Community 90 - "Cosmos Artifact Store"
Cohesion: 0.22
Nodes (8): Artifact Types, Auth Modes, Cosmos Artifact Store, Deprecated Local Script Names, Document Shape, Initialize, Smoke Test, Troubleshooting

### Community 91 - "Deployment Readiness Checklist"
Cohesion: 0.22
Nodes (8): 1. Source Readiness, 2. Dependency Readiness, 3. Config Readiness, 4. Storage Readiness, 5. Observability Readiness, 6. Runtime Smoke, 7. Known Out Of Scope, Deployment Readiness Checklist

### Community 93 - "make_decision"
Cohesion: 0.21
Nodes (11): _decision_json(), _on_bucket_retry(), One audited routing decision made by the graph., RoutingDecision, append_decision(), make_decision(), Any, Helpers for recording routing decisions in graph state. (+3 more)

### Community 94 - "smoke_keyvault_config.py"
Cohesion: 0.24
Nodes (8): _build_parser(), main(), ArgumentParser, Live smoke-check for fetching the DoD agent JSON config secret., Any, Tests for enterprise runtime config smoke scripts., test_enterprise_runtime_smoke_default_mode_does_not_call_azure(), test_keyvault_config_smoke_imports_without_calling_azure()

### Community 95 - ".settings_customise_sources"
Cohesion: 0.29
Nodes (6): _enterprise_runtime_config_source(), Any, Normalize backward-compatible enterprise aliases., Place Key Vault JSON config after process env and before `.env`., BaseSettings, PydanticBaseSettingsSource

### Community 96 - ".get_pull_request"
Cohesion: 0.08
Nodes (30): Shared Azure DevOps REST client foundation., AzureDevOpsGitClient, Any, Azure DevOps Git API client., Git and pull-request lookup operations for build context., Query pull requests related to a commit., Get a single pull-request record., Get pull-request commit list. (+22 more)

### Community 97 - "Key Vault Config Contract"
Cohesion: 0.29
Nodes (6): Key Vault Config Contract, Never Store, Optional Keys, Required Keys, Rotation And Changes, Sample Secret

### Community 98 - "LangSmith Observability"
Cohesion: 0.29
Nodes (6): Configuration, LangSmith Observability, Local Validation, Troubleshooting Missing Traces, What Is Never Traced, What Is Traced

### Community 99 - "langgraph.json"
Cohesion: 0.29
Nodes (6): dependencies, env, graphs, dod, image_distro, .

### Community 100 - "test_dod_runs_rule_evaluation_api.py"
Cohesion: 0.57
Nodes (6): _patch_settings(), MonkeyPatch, Path, Tests for Phase 9 read-only rule evaluation endpoint., test_get_rule_evaluation_returns_artifact_content(), test_missing_rule_evaluation_returns_404()

### Community 101 - "_required_cosmos_config"
Cohesion: 0.50
Nodes (7): _required_cosmos_config(), Any, Tests for Cosmos default credential configuration., _settings(), test_cosmos_default_credential_does_not_require_cosmos_key(), test_cosmos_emulator_key_mode_requires_cosmos_key(), test_cosmos_key_mode_requires_cosmos_key()

### Community 102 - ".get_test_results"
Cohesion: 0.40
Nodes (3): Any, Return test runs associated with a build., Return test results for a test run.

### Community 103 - "resolve_runtime_config"
Cohesion: 0.38
Nodes (6): Resolve enterprise runtime config with process env overriding Key Vault JSON., resolve_runtime_config(), Tests for enterprise runtime config merge precedence., test_env_vars_override_key_vault_json_values(), test_key_vault_json_fills_missing_env_values(), test_langgraph_assistant_id_defaults_to_dod()

### Community 104 - "DoD Run Contract"
Cohesion: 0.40
Nodes (4): DoD Run Contract, Input, Invocation Notes, Output

### Community 105 - "test_dockerignore_rules.py"
Cohesion: 0.60
Nodes (4): _dockerignore_lines(), Tests for Docker build context safety rules., test_dockerignore_does_not_exclude_langgraph_config(), test_dockerignore_excludes_secrets_and_generated_artifacts()

### Community 107 - "normalized_words"
Cohesion: 0.33
Nodes (7): longest_contiguous_word_overlap(), normalized_words(), Return lowercase word tokens used by conservative overlap checks., Return a normalized word-sequence similarity score., Return the longest contiguous word run shared by both values., _remove_repeated_justification_sentences(), sequence_similarity()

### Community 108 - "test_normalize_endpoint_returns_expected_summary"
Cohesion: 0.67
Nodes (3): MonkeyPatch, Normalize endpoint should return safe summary with canonical path., test_normalize_endpoint_returns_expected_summary()

## Knowledge Gaps
- **76 isolated node(s):** `.`, `dod`, `image_distro`, `env`, `ado-dod-agent` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `test_dod_runs_artifact_api.py` to `AzureDevOpsBaseClient`, `config.py`, `Settings`, `collect_raw_metadata`, `smoke_ado_auth.py`, `FakeStore`, `CosmosArtifactStore`, `CombinedLlmOutputs`, `langsmith_tracing.py`, `LocalJsonStore`, `evaluate_rules.py`, `canonical.py`, `get_langgraph_api_key`, `run_dod_workflow`, `smoke_enterprise_runtime_config.py`, `AzureFoundryChatClient`, `Any`, `smoke_cosmos.py`, `validate_service_now_payload.py`, `_required_cosmos_config`, `smoke_llm_access.py`, `normalize_raw_metadata.py`, `run_dod_agent`, `cosmos_artifact_store.py`, `test_llm_generator.py`, `run_dod_agent.py`, `test_dod_graph_advanced_nodes.py`, `build_evidence_buckets.py`, `init_cosmos.py`, `test_cosmos_document_type.py`, `.output_path`, `smoke_keyvault_config.py`, `get_storage_store`, `.settings_customise_sources`, `.get_pull_request`, `test_dod_runs_rule_evaluation_api.py`, `_required_cosmos_config`, `resolve_runtime_config`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `LocalJsonStore` connect `Any` to `test_dod_runs_rule_evaluation_api.py`, `dod_runs.py`, `build_evidence_buckets.py`, `DodGraphState`, `test_dod_runs_artifact_api.py`, `Any`, `nodes.py`, `.load_artifact`, `validate_service_now_payload.py`, `.output_path`, `LocalJsonStore`, `generate_service_now_fields.py`, `get_storage_store`, `evaluate_rules.py`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `smoke_llm_access.py` to `config.py`, `dod_runs.py`, `smoke_ado_auth.py`, `DodGraphState`, `RuleResult`, `nodes.py`, `langsmith_tracing.py`, `evaluate_rules.py`, `smoke_enterprise_runtime_config.py`, `Any`, `validate_service_now_payload.py`, `normalize_raw_metadata.py`, `run_dod_agent`, `cosmos_artifact_store.py`, `generator.py`, `generate_service_now_fields.py`, `azure_foundry_client.py`, `run_dod_agent.py`, `build_evidence_buckets.py`, `test_dod_runs_artifact_api.py`, `Any`, `.output_path`, `get_storage_store`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `Settings` (e.g. with `AzureDevOpsBaseClient` and `AzureDevOpsClientConfig`) actually correct?**
  _`Settings` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `LocalJsonStore` (e.g. with `Settings` and `test_local_json_backend_selects_local_store()`) actually correct?**
  _`LocalJsonStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `CosmosArtifactStore` (e.g. with `Settings` and `run_container_readiness()`) actually correct?**
  _`CosmosArtifactStore` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `.`, `dod`, `image_distro` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._