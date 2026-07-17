# Graph Report - ado-dod-agent  (2026-07-17)

## Corpus Check
- 268 files · ~102,306 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2782 nodes · 7346 edges · 134 communities (121 shown, 13 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 257 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d23ae3cc`
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
- validate_env.py
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
- test_credentials.py
- .__init__
- .get_token
- test_smoke_azure_credentials.py
- test_normalize_endpoint_returns_expected_summary
- test_orchestration_storage_integration.py

## God Nodes (most connected - your core abstractions)
1. `Settings` - 200 edges
2. `LocalJsonStore` - 95 edges
3. `get_settings()` - 74 edges
4. `CosmosArtifactStore` - 65 edges
5. `build_evidence_bundle()` - 45 edges
6. `_TimelineDescendant` - 42 edges
7. `DodGraphState` - 39 edges
8. `validate_bucket_3_fields()` - 39 edges
9. `CanonicalDodDocument` - 37 edges
10. `_complete_canonical()` - 37 edges

## Surprising Connections (you probably didn't know these)
- `_Execution` --uses--> `Settings`  [INFERRED]
  tests/unit/test_canonical_normalization_state.py → backend/app/utils/config.py
- `_Items` --uses--> `Settings`  [INFERRED]
  tests/unit/test_canonical_normalization_state.py → backend/app/utils/config.py
- `_Metadata` --uses--> `Settings`  [INFERRED]
  tests/unit/test_canonical_normalization_state.py → backend/app/utils/config.py
- `_Quality` --uses--> `Settings`  [INFERRED]
  tests/unit/test_canonical_normalization_state.py → backend/app/utils/config.py
- `_Risk` --uses--> `Settings`  [INFERRED]
  tests/unit/test_canonical_normalization_state.py → backend/app/utils/config.py

## Import Cycles
- None detected.

## Communities (134 total, 13 thin omitted)

### Community 0 - "builder.py"
Cohesion: 0.13
Nodes (18): DodRunSummary, BaseModel, Phase 7A orchestration run summary models., Structured non-sensitive issue captured during orchestration., Persisted summary for one end-to-end DoD agent run., RunIssue, Any, Tests for shared DoD run contract models. (+10 more)

### Community 1 - "AzureDevOpsBaseClient"
Cohesion: 0.05
Nodes (52): AsyncClient, AzureDevOpsBaseClient, AzureDevOpsClientConfig, AzureDevOpsClientError, Exception, Shared Azure DevOps REST client foundation., Close owned HTTP client resources., Configuration for Azure DevOps REST API access. (+44 more)

### Community 2 - "config.py"
Cohesion: 0.04
Nodes (68): AccessToken, correlation_id_middleware(), lifespan(), Response, FastAPI entrypoint for ado-dod-agent., Initialize runtime resources at startup., Attach a correlation id to logs and responses for each request., Smoke validation endpoints. (+60 more)

### Community 3 - "Settings"
Cohesion: 0.11
Nodes (25): Resolve enterprise runtime config with process env overriding Key Vault JSON., resolve_runtime_config(), _build_parser(), build_settings_from_sources(), load_mock_key_vault_config(), main(), Any, ArgumentParser (+17 more)

### Community 4 - "raw_metadata.py"
Cohesion: 0.12
Nodes (36): Models package exports., BuildEvidenceResponse, HealthResponse, NormalizeRawResponse, BaseModel, Output schemas returned by API endpoints., Service liveness payload., Placeholder run generation response for Phase 0. (+28 more)

### Community 5 - "dod_runs.py"
Cohesion: 0.06
Nodes (62): ApiIssue, ArtifactResponse, GenerateRunRequest, GenerateRunResponse, BaseModel, API request/response models for Phase 8 pipeline-facing endpoints., Request body for running the DoD agent workflow., API-safe issue model. (+54 more)

### Community 6 - "collect_raw_metadata"
Cohesion: 0.07
Nodes (45): CollectRawInput, GenerateRunInput, Input schemas for API operations., Phase-2 request model for raw metadata collection., Phase-0 placeholder payload for generate-run orchestration., collect_raw(), Collect raw build metadata and persist local artifacts., _as_collect_input() (+37 more)

### Community 7 - "smoke_ado_auth.py"
Cohesion: 0.08
Nodes (51): _timed_node(), assert_json_serializable(), _assert_not_cycle(), classify_platform_persistence_failure(), estimate_json_size_bytes(), exception_type_chain(), find_non_json_serializable_paths(), graph_state_diagnostics() (+43 more)

### Community 8 - "dod_contracts.py"
Cohesion: 0.10
Nodes (37): _derive_rule_evaluation_summary(), _derive_run_summary_rules(), _dict_or_empty(), DoDRuleEvaluationSummary, DoDRunArtifactPaths, DoDRunError, DoDRunInput, DoDRunOutput (+29 more)

### Community 9 - "FakeStore"
Cohesion: 0.11
Nodes (19): _base_state(), _fake_llm_outputs(), _fake_validated(), FakeModel, FakeStore, Any, MonkeyPatch, Path (+11 more)

### Community 10 - "DodGraphState"
Cohesion: 0.16
Nodes (26): LangGraph workflow package., generate_llm_outputs_node(), _generate_llm_outputs_once(), _on_bucket_retry(), Run Phase 5B LLM generation with bucket-level retry., DodGraphState, TypedDict, LangGraph state definitions for Phase 7B DoD orchestration. (+18 more)

### Community 11 - "test_bucket_prompts.py"
Cohesion: 0.07
Nodes (41): build_prompt(), Any, Prompt builder for Phase 5B change intent fields., Build the bucket 1 prompt from deterministic evidence only., _strategy_guidance(), build_prompt(), Any, Prompt builder for Phase 5B execution and validation fields. (+33 more)

### Community 12 - "get_azure_credential"
Cohesion: 0.25
Nodes (13): FakeClientSecretCredential, FakeDefaultAzureCredential, FakeManagedIdentityCredential, _install_fake_azure_identity(), Any, MonkeyPatch, Tests for the centralized Azure credential factory., test_client_secret_mode_creates_client_secret_credential() (+5 more)

### Community 13 - "output_repair.py"
Cohesion: 0.13
Nodes (42): format_backout_minutes(), Format rounded minutes without seconds or false precision., _backout_steps_for_actions(), _best_lower_environment_stage_duration(), _brief_backout_mitigation(), bucket_3_claim_evidence_text(), bucket_3_evidence(), _build_backout_plan() (+34 more)

### Community 14 - "RuleResult"
Cohesion: 0.12
Nodes (34): ConfidenceAdjustment, BaseModel, Deterministic rule evaluation models for Phase 9., Base config for rule evaluation payloads., RuleBaseModel, RuleEvaluation, RuleEvaluationSummary, RuleResult (+26 more)

### Community 15 - "nodes.py"
Cohesion: 0.10
Nodes (49): assemble_run_result_node(), _bucket_3_state_summary(), build_evidence_buckets_node(), _coerce_build_id(), _coerce_float(), _coerce_str(), collect_raw_metadata_node(), _collector_issue() (+41 more)

### Community 16 - "select_prompt_strategy"
Cohesion: 0.11
Nodes (37): persist_routing_decisions_node(), Persist Phase 7B routing decisions under data/output/{build_id}., EvidenceQualityAssessment, PromptStrategySelection, BaseModel, Deterministic routing models for Phase 7B orchestration., One audited routing decision made by the graph., Quality assessment for prompt-ready evidence buckets. (+29 more)

### Community 17 - "test_evidence_builder.py"
Cohesion: 0.13
Nodes (41): CanonicalArtifact, CanonicalBaseModel, CanonicalCommit, CanonicalPullRequest, CanonicalTestResult, CanonicalTestRun, CanonicalTestSummary, CanonicalWorkItem (+33 more)

### Community 18 - "CosmosArtifactStore"
Cohesion: 0.16
Nodes (7): _content_from_document(), CosmosArtifactStore, Any, Load run summary by run id or by build id for endpoint compatibility., Cosmos-backed artifact store for local emulator and enterprise runtime., Load one artifact by run id and artifact type., Load the newest matching artifact for a build id.

### Community 19 - "dod_deployment_graph.py"
Cohesion: 0.11
Nodes (27): _deployment_state_failure(), make_graph_dod(), Any, LangGraph deployment adapter for the DoD agent., Compile the enterprise LangGraph deployment graph for the DoD assistant., _run_dod_node(), _validate_deployment_state(), DoDGraphState (+19 more)

### Community 20 - "canonical.py"
Cohesion: 0.21
Nodes (34): CanonicalScanSummary, _as_dict(), _as_float(), _as_int(), _as_list(), _as_str(), build_canonical_summary(), _contains_any() (+26 more)

### Community 21 - "CombinedLlmOutputs"
Cohesion: 0.12
Nodes (25): Bucket1GeneratedOutput, Bucket2GeneratedOutput, Bucket3GeneratedOutput, LlmModelMetadata, LlmOutputBaseModel, BaseModel, Base config for generated LLM output models., _combined_outputs() (+17 more)

### Community 22 - "langsmith_tracing.py"
Cohesion: 0.06
Nodes (61): Observability helpers for DoD agent tracing., build_run_metadata(), _duration_ms(), get_trace_mode(), is_tracing_enabled(), _langsmith_client(), _phase_durations(), _project_name() (+53 more)

### Community 23 - "LocalJsonStore"
Cohesion: 0.06
Nodes (38): Local JSON storage abstraction for raw metadata artifacts., get_storage_store(), Storage backend selection for DoD artifacts., Return the configured artifact store., Runtime configuration loaded from environment variables., Any, Tests for the common artifact store contract., test_local_json_store_satisfies_artifact_store_contract() (+30 more)

### Community 24 - "load_agent_config_from_key_vault"
Cohesion: 0.16
Nodes (21): create_default_azure_credential(), EnterpriseConfigError, load_agent_config_from_key_vault(), parse_agent_config_json(), ValueError, Backward-compatible wrapper for the centralized Azure credential factory., Load optional agent config JSON from Key Vault without printing values., Parse and validate the DoD agent Key Vault JSON config contract. (+13 more)

### Community 25 - "DodRunSummary"
Cohesion: 0.36
Nodes (14): Any, MonkeyPatch, Tests for Phase 8 /api/v1/runs/generate endpoint., _request(), _summary(), test_generate_endpoint_accepts_x_correlation_id_header(), test_generate_endpoint_body_correlation_id_overrides_header(), test_generate_endpoint_calls_run_dod_agent() (+6 more)

### Community 26 - "output_validator.py"
Cohesion: 0.21
Nodes (28): ValidationIssue, _as_dict(), _backout_derivation_issues(), _bucket(), _candidate_has_valid_timing(), _expected_application_display(), _issue(), _missing_context_issues() (+20 more)

### Community 27 - "service.py"
Cohesion: 0.24
Nodes (15): TraceabilityReport, BucketValidationResult, ConfidenceScore, BaseModel, Validated Phase 6 ServiceNow-ready output models., Base config for validated output payloads., ValidatedDodOutput, ValidatedOutputBaseModel (+7 more)

### Community 28 - "extract_json_object"
Cohesion: 0.20
Nodes (14): _candidate_json_strings(), _extract_balanced_object(), extract_json_object(), JsonParseError, Any, Defensive JSON object extraction for LLM responses., Raised when an LLM response cannot be parsed as one JSON object., Extract and parse a JSON object from raw LLM text. (+6 more)

### Community 29 - "validate_bucket_3_fields"
Cohesion: 0.19
Nodes (37): Normalize Bucket 3 fields to concise, evidence-grounded ServiceNow text., repair_bucket_3_fields(), Validate concise, evidence-grounded backout and risk field intent., validate_bucket_3_fields(), test_validator_flags_legacy_empty_activity_rejection_and_incomplete_traversal(), _assert_narrative_risk_format(), _evidence(), _labeled_risk_text() (+29 more)

### Community 30 - "evaluate_rules.py"
Cohesion: 0.13
Nodes (28): _build_parser(), build_summary(), format_summary(), _load_optional(), _load_required(), main(), Any, ArgumentParser (+20 more)

### Community 31 - "canonical.py"
Cohesion: 0.21
Nodes (25): CanonicalDodDocument, ChangeContext, ExecutionContext, NormalizationMetadata, QualityContext, Canonical normalized models for Phase 3., RiskContext, RunContext (+17 more)

### Community 32 - "render_workflow_ascii.py"
Cohesion: 0.16
Nodes (27): build_ascii_from_workflow(), _build_parser(), _conditional_edges_by_source(), _continue_target(), _display_node(), _edge_with_label(), GraphEdge, _linear_chain() (+19 more)

### Community 33 - "get_langgraph_api_key"
Cohesion: 0.26
Nodes (11): _present_value(), Any, Enterprise runtime config resolution for the DoD agent., Validate key names and required enterprise config shape without values., validate_key_vault_config_contract(), Tests for the DoD Key Vault JSON config contract., test_agent_config_contract_rejects_actual_langgraph_api_key(), test_contract_rejects_artifact_payload_keys() (+3 more)

### Community 34 - "run_dod_workflow"
Cohesion: 0.25
Nodes (25): Run the Phase 7A workflow and return final graph state., run_dod_workflow(), _input(), _patch_common(), Any, MonkeyPatch, Tests for Phase 7B advanced workflow routing., test_completed_with_warnings_still_works() (+17 more)

### Community 35 - "smoke_enterprise_runtime_config.py"
Cohesion: 0.24
Nodes (19): normalize_raw_bundle(), Normalize a Phase-2 raw bundle into canonical deterministic structure., _build_complete_raw_bundle(), _bundle_with_message(), Any, Tests for deterministic canonical normalizer., test_complete_raw_bundle_normalizes_successfully(), test_missing_tests_does_not_fail() (+11 more)

### Community 36 - "AzureFoundryChatClient"
Cohesion: 0.21
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
Cohesion: 0.17
Nodes (22): FieldTraceability, BaseModel, Traceability report models for ServiceNow payload generation., Base config for traceability payloads., TraceabilityBaseModel, build_traceability_report(), _dict_list(), _optional_dict() (+14 more)

### Community 41 - "redaction.py"
Cohesion: 0.15
Nodes (14): _Document, _Execution, _Items, _Metadata, Any, MonkeyPatch, _Quality, Canonical node tests for artifact-first compact state updates. (+6 more)

### Community 42 - "assess_risk_tier"
Cohesion: 0.10
Nodes (42): _as_dict(), _as_int(), _as_list(), _as_str(), _assess_bucket_1(), _assess_bucket_2(), _assess_bucket_3(), assess_evidence_quality() (+34 more)

### Community 43 - "invoke_dod_langgraph.py"
Cohesion: 0.12
Nodes (21): _build_parser(), build_structured_input(), format_safe_summary(), invoke_dod_assistant(), main(), Any, ArgumentParser, Namespace (+13 more)

### Community 44 - "test_completeness.py"
Cohesion: 0.27
Nodes (22): _all_text(), _bucket(), calculate_test_completeness_score(), evaluate_test_completeness_rules(), has_artifact_evidence(), _has_failed_signal(), has_failed_tests(), has_security_scan_signals() (+14 more)

### Community 45 - "assess_evidence_quality"
Cohesion: 0.17
Nodes (14): _build_parser(), format_summary(), main(), Any, ArgumentParser, Namespace, CLI entrypoint for Phase-3 canonical normalization., Render a safe, compact summary for console output. (+6 more)

### Community 46 - "smoke_cosmos.py"
Cohesion: 0.16
Nodes (17): _build_parser(), load_env_local(), Deprecated wrapper for local Cosmos artifact smoke testing., main(), _missing_full_run_config(), ArgumentParser, Path, Smoke-test the configured Cosmos artifact store. (+9 more)

### Community 47 - "validate_service_now_payload.py"
Cohesion: 0.15
Nodes (27): _build_parser(), build_summary(), format_summary(), _load_evidence_bundle(), _load_llm_outputs(), main(), persist_outputs(), Any (+19 more)

### Community 48 - "clean_servicenow_field_text"
Cohesion: 0.16
Nodes (19): clean_servicenow_field_text(), normalize_servicenow_whitespace(), Clean one ServiceNow field without changing business meaning., Remove raw/internal reference tokens from field text., Normalize whitespace while preserving meaningful numbered lists., Remove markdown code fences from generated text., remove_markdown_artifacts(), remove_raw_reference_tokens() (+11 more)

### Community 49 - "_required_cosmos_config"
Cohesion: 0.18
Nodes (14): _required_cosmos_config(), FakeContainer, Any, Tests for the official Cosmos artifact store without an emulator., _settings(), test_cosmos_config_default_credential_does_not_require_key(), test_cosmos_config_requires_key_for_key_modes(), test_save_load_and_list_with_mocked_container() (+6 more)

### Community 50 - ".save_output_json"
Cohesion: 0.20
Nodes (14): normalize_field_aliases(), Extract one JSON object from raw text without evaluating code., Normalize common field aliases without changing business content., Repair structural fields required by Phase 5B output models., _repair_confidence(), repair_json_text(), repair_llm_output_shape(), Tests for deterministic Phase 6 output repair. (+6 more)

### Community 51 - "test_output_validator.py"
Cohesion: 0.20
Nodes (19): detect_raw_reference_leakage(), Return whether text contains raw/internal evidence references., Validate that final ServiceNow fields do not expose internal evidence refs., validate_no_raw_reference_leakage(), evidence_bundle(), _issues(), Tests for deterministic Phase 6 output validation., test_absolute_no_risk_claim_is_flagged() (+11 more)

### Community 52 - "README.md"
Cohesion: 0.10
Nodes (19): Auth, Backend Layout, Backout Plan, Commands, Current Phase Scope, Endpoints, Phase 2 Raw Collection, Phase 3 Canonical Normalization (+11 more)

### Community 53 - "smoke_container_readiness.py"
Cohesion: 0.18
Nodes (17): graph_entrypoint(), load_langgraph_config(), main(), Any, Path, Smoke-check container readiness for LangGraph-native DoD deployment., Load and validate the LangGraph config file shape., Return the configured graph entrypoint for a graph name. (+9 more)

### Community 54 - "smoke_llm_access.py"
Cohesion: 0.22
Nodes (13): endpoint_host(), format_success_summary(), _is_azure_auth_failure(), _is_azure_http_failure(), main(), Exception, Smoke test Azure OpenAI-compatible Foundry model access using Entra ID., Return only the host portion of the configured endpoint. (+5 more)

### Community 55 - "normalize_raw_metadata.py"
Cohesion: 0.16
Nodes (11): ChatModel, _extract_content_part(), _is_placeholder(), _parse_json_object(), Any, Protocol, Azure OpenAI-compatible Foundry chat client using Entra ID auth., Minimal protocol for LangChain chat models used by this wrapper. (+3 more)

### Community 56 - "normalize_raw_bundle"
Cohesion: 0.19
Nodes (14): build_headers(), build_health_url(), _build_parser(), check_health(), main(), ArgumentParser, Smoke-check the deployed LangGraph platform health endpoint., Return the deployed LangGraph /ok health URL for a base URL. (+6 more)

### Community 57 - "run_dod_agent"
Cohesion: 0.16
Nodes (17): _load_persisted_summary(), _parse_datetime(), Any, datetime, Service entry point for Phase 7A DoD agent orchestration., Run the DoD agent workflow and return the persisted run summary model., Load the persisted summary after the graph has compacted it out of state., run_dod_agent() (+9 more)

### Community 58 - "cosmos_artifact_store.py"
Cohesion: 0.15
Nodes (8): _artifact_from_relative_path(), _artifact_type_from_filename(), _compat_uri(), Path, Official Cosmos DB artifact store for DoD run artifacts., Compatibility no-op for file-backed collection code., _run_id_for_build(), _run_id_from_payload()

### Community 59 - "test_llm_generator.py"
Cohesion: 0.29
Nodes (16): _bucket_1_response(), _bucket_2_response(), _bucket_3_response(), DummyClient, _evidence_bundle(), Any, MonkeyPatch, Tests for Phase 5B LLM generator service. (+8 more)

### Community 60 - "generator.py"
Cohesion: 0.24
Nodes (16): generate_all_buckets(), _generate_bucket(), generate_bucket_1(), generate_bucket_2(), generate_bucket_3(), _generate_bucket_with_retry(), _optional_str(), Any (+8 more)

### Community 61 - "evaluate_risk_rules"
Cohesion: 0.23
Nodes (16): evaluate_risk_rules(), _mentions(), _overall_confidence(), Any, Risk and impact consistency rules., Evaluate risk and impact consistency rules., _risk_flags(), _risk_tier() (+8 more)

### Community 62 - "generate_service_now_fields.py"
Cohesion: 0.20
Nodes (17): _build_parser(), build_summary(), format_summary(), _load_evidence_inputs(), main(), persist_outputs(), Any, ArgumentParser (+9 more)

### Community 63 - "bucket_3_selection.py"
Cohesion: 0.05
Nodes (118): ApplicationCandidateScoreEvidence, ApplicationResolutionEvidence, ArtifactEvidence, BackoutStepDerivationEvidence, BackoutStepIgnoredTaskEvidence, BackoutStepSourceTaskEvidence, BackoutTimeDerivationEvidence, ChangeIntentEvidence (+110 more)

### Community 64 - "evaluate_unsupported_claim_rules"
Cohesion: 0.24
Nodes (15): _approval_supported(), _contains_any(), evaluate_unsupported_claim_rules(), _field_text(), Any, Rules for unsupported claims in generated ServiceNow field text., Evaluate unsupported AI-generated claim rules., _rollback_supported() (+7 more)

### Community 65 - "azure_foundry_client.py"
Cohesion: 0.25
Nodes (10): get_langgraph_api_key_config(), get_redacted_langgraph_api_key_summary(), LangGraphApiKeyConfig, _present_value(), Any, LangGraph API key retrieval for external invocation helpers., LangGraph API invocation config that is safe to summarize., Return LangGraph API-key config from environment with safe defaults. (+2 more)

### Community 66 - "LangGraph Deployment"
Cohesion: 0.12
Nodes (16): Confirmed Org Deployment Path, Container Build Smoke, Contract Smoke Test, Cosmos Guidance, Graph Registration, LangGraph Deployment, LangGraph SDK Invocation, LangGraph state versus artifact storage (+8 more)

### Community 67 - "run_dod_agent.py"
Cohesion: 0.16
Nodes (22): _build_parser(), _evidence_quality_summary(), format_summary(), _load_routing_payload(), main(), _overall_confidence(), _prompt_strategy_summary(), Any (+14 more)

### Community 68 - "smoke_langgraph_health.py"
Cohesion: 0.18
Nodes (15): get_langgraph_api_key(), LangGraphApiKeyConfigError, ValueError, Fetch the LangGraph API key string from Key Vault for external callers., Raised when LangGraph API key retrieval config is invalid., Validate LangGraph API-key Key Vault pointer without fetching the secret., validate_langgraph_api_key_config(), FakeSecret (+7 more)

### Community 69 - "test_dod_graph_advanced_nodes.py"
Cohesion: 0.13
Nodes (27): assess_evidence_quality_node(), assess_risk_tier_node(), _decision_json(), _load_evidence_bundle_from_state(), BaseException, Assess evidence quality for downstream routing., Assess risk tier for downstream prompt strategy and final routing., Select deterministic prompt strategies for each bucket. (+19 more)

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
Cohesion: 0.18
Nodes (22): build_source_ref_map_entry(), _display_name(), _first_value(), _get_value(), normalize_source_ref(), Any, Friendly evidence source reference normalization., Return a friendly source reference and traceability map entry. (+14 more)

### Community 74 - "test_change_intent_field_separation.py"
Cohesion: 0.31
Nodes (9): Conservatively repair delivery leakage and repeated description sentences., repair_change_intent_fields(), _evidence_bundle(), _full_llm_output(), Focused tests for change-description and justification field separation., test_final_payload_repairs_fields_and_preserves_eight_field_contract(), test_repair_condenses_repeated_description_when_supported_rationale_remains(), test_repair_removes_delivery_metadata_and_retains_functional_change() (+1 more)

### Community 75 - "Enterprise Runtime Config"
Cohesion: 0.17
Nodes (11): Azure Credential, Confirmed Deployment Model, Enterprise Runtime Config, Key Vault JSON, LangGraph API Key Secret, LangGraph Platform Variables, LangSmith, Local Development (+3 more)

### Community 76 - "init_cosmos.py"
Cohesion: 0.23
Nodes (10): _build_parser(), load_env_local(), Deprecated wrapper for local Cosmos initialization., main(), ArgumentParser, Namespace, Path, Initialize the configured Cosmos artifact store database/container. (+2 more)

### Community 77 - "test_dod_runs_artifact_api.py"
Cohesion: 0.07
Nodes (49): Return safe validation errors/warnings for the optional Key Vault pointer., validate_agent_config_pointer(), Path, Return all data directories used by the pipeline lifecycle., Return official Cosmos auth mode, honoring deprecated local aliases., Return official Cosmos endpoint, honoring deprecated local aliases., Return official Cosmos key, honoring deprecated local aliases., Return official Cosmos database, honoring deprecated local aliases. (+41 more)

### Community 78 - "Any"
Cohesion: 0.12
Nodes (12): collect_execution_context(), Any, Collect timeline and artifacts with safe partial-failure behavior., collect_quality_context(), Any, Collect test runs and test results with partial-failure handling., ArtifactStore, Any (+4 more)

### Community 79 - ".load_artifact"
Cohesion: 0.20
Nodes (5): Return canonical local path for a Phase R3 traceability report., Return canonical local path for a Phase 9 rule evaluation artifact., Return canonical local path for a Phase 7A run summary., Return canonical local path for a Phase 7B routing decisions artifact., Return canonical local path for a generated output artifact file.

### Community 80 - "test_cosmos_document_type.py"
Cohesion: 0.31
Nodes (7): FakeContainer, Any, Tests for Cosmos document_type compatibility fields., _settings(), test_cosmos_artifact_write_includes_artifact_document_type(), test_cosmos_read_remains_compatible_when_document_type_missing(), test_cosmos_run_summary_write_includes_run_summary_document_type()

### Community 81 - "._get_container"
Cohesion: 0.11
Nodes (11): _cosmos_uri(), _document_type_for_artifact(), _make_json_safe(), List artifact types stored for a run id., Save a run summary artifact., Delete one smoke-test artifact if it exists., Return the stable Cosmos document id for an artifact., Create the configured database and container if missing. (+3 more)

### Community 82 - ".output_path"
Cohesion: 0.33
Nodes (6): Depends, Perform a minimal Azure DevOps Entra auth smoke check., smoke_ado_auth(), MonkeyPatch, run_smoke should compose summary using mocked dependencies., test_run_smoke_with_mocked_client()

### Community 83 - "smoke_azure_credentials.py"
Cohesion: 0.33
Nodes (17): CanonicalJob, CanonicalStage, CanonicalTask, _container_activity_items(), Return every descendant in timeline order, with cycle protection and ancestry., _backout(), _canonical(), Focused tests for activity-independent timing and recursive backout derivation. (+9 more)

### Community 84 - "smoke_keyvault_config.py"
Cohesion: 0.27
Nodes (9): _checkpoint_state(), Any, MonkeyPatch, Tests for the compact orchestration-state contract and merge behavior., test_artifact_references_replace_prior_values_without_accumulation(), test_input_normalization_clears_legacy_large_state_values(), test_timed_node_compacts_oversized_update_before_checkpoint(), test_timed_node_records_soft_size_warning_once() (+1 more)

### Community 85 - "test_field_quality_rules.py"
Cohesion: 0.47
Nodes (9): _ids(), _payload(), Tests for ServiceNow field quality rules., test_duplicate_content_triggers_rule(), test_empty_field_triggers_rule(), test_generic_validation_plan_triggers_rule(), test_long_short_description_triggers_rule(), test_markdown_triggers_rule() (+1 more)

### Community 86 - "test_test_completeness_rules.py"
Cohesion: 0.42
Nodes (9): _empty_evidence(), Tests for Phase 9 test completeness scoring and rules., _rules(), test_failed_tests_trigger_rule(), test_missing_nonfunctional_evidence_triggers_rule(), test_no_test_evidence_triggers_no_automated_results(), test_score_is_low_when_no_test_or_validation_evidence_exists(), test_score_is_medium_when_tests_missing_but_validation_exists() (+1 more)

### Community 87 - "test_validate_service_now_payload_script.py"
Cohesion: 0.16
Nodes (23): AzureCredentialConfigError, get_azure_credential(), get_azure_credential_mode(), get_redacted_credential_summary(), _managed_identity_client_id(), _present(), _present_value(), Any (+15 more)

### Community 88 - "test_validated_output_models.py"
Cohesion: 0.48
Nodes (11): _patch_settings(), MonkeyPatch, Path, Tests for Phase 8 read-only artifact endpoints., test_get_confidence_returns_confidence_content(), test_get_payload_returns_service_now_payload_content(), test_get_routing_decisions_returns_routing_content(), test_get_summary_returns_run_summary_content() (+3 more)

### Community 89 - "get_storage_store"
Cohesion: 0.18
Nodes (6): Any, Return a single build record., Return timeline details for a build., Return linked work-item references for a build., Return source-control changes associated with a build., Return build artifact metadata.

### Community 90 - "Cosmos Artifact Store"
Cohesion: 0.22
Nodes (8): Artifact Types, Auth Modes, Cosmos Artifact Store, Deprecated Local Script Names, Document Shape, Initialize, Smoke Test, Troubleshooting

### Community 91 - "Deployment Readiness Checklist"
Cohesion: 0.22
Nodes (8): 1. Source Readiness, 2. Dependency Readiness, 3. Config Readiness, 4. Storage Readiness, 5. Observability Readiness, 6. Runtime Smoke, 7. Known Out Of Scope, Deployment Readiness Checklist

### Community 92 - "build_key_vault_headers"
Cohesion: 0.27
Nodes (4): Any, Response, Execute an authenticated GET request and return a JSON object., Execute an authenticated POST request and return a JSON object.

### Community 93 - "make_decision"
Cohesion: 0.13
Nodes (24): CombinedLlmOutputs, Pydantic models for Phase 5B generated ServiceNow field drafts., ServiceNowPayload, format_service_now_payload(), Return a clean ServiceNow payload with exactly the eight supported fields., assemble_service_now_payload(), Any, Assemble flat ServiceNow payloads from Phase 5B bucket outputs. (+16 more)

### Community 94 - "smoke_keyvault_config.py"
Cohesion: 0.50
Nodes (4): _build_parser(), main(), ArgumentParser, Live smoke-check for fetching the DoD agent JSON config secret.

### Community 95 - ".settings_customise_sources"
Cohesion: 0.29
Nodes (6): _enterprise_runtime_config_source(), Any, Normalize backward-compatible enterprise aliases., Place Key Vault JSON config after process env and before `.env`., BaseSettings, PydanticBaseSettingsSource

### Community 96 - ".get_pull_request"
Cohesion: 0.21
Nodes (13): AzureDevOpsWorkItemClient, Any, Work-item operations for raw metadata hydration., Hydrate work items in a batch request., collect_change_context(), _extract_pull_request_ids(), _extract_work_item_ids(), _hydrate_work_items() (+5 more)

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
Cohesion: 0.33
Nodes (8): build_key_vault_headers(), Build auth headers from the LangGraph API-key Key Vault secret., Any, Tests for the deployed LangGraph /ok health smoke script., test_api_key_header_is_not_printed(), test_health_help_works_without_network(), test_key_vault_api_key_header_defaults_to_x_api_key(), test_key_vault_api_key_header_respects_config()

### Community 102 - ".get_test_results"
Cohesion: 0.40
Nodes (3): Any, Return test runs associated with a build., Return test results for a test run.

### Community 103 - "resolve_runtime_config"
Cohesion: 0.47
Nodes (5): Path, Tests for Phase 8 readiness endpoint., test_ready_does_not_call_ado_or_llm(), test_ready_returns_503_when_required_config_missing(), test_ready_returns_ready_when_required_config_present()

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
Cohesion: 0.29
Nodes (4): Any, Query pull requests related to a commit., Get a single pull-request record., Get pull-request commit list.

### Community 109 - "validate_env.py"
Cohesion: 0.47
Nodes (5): Any, MonkeyPatch, Tests for the LLM smoke access script., test_smoke_script_does_not_print_tokens_or_authorization_headers(), test_smoke_script_returns_success_with_mocked_client()

### Community 128 - "test_credentials.py"
Cohesion: 0.40
Nodes (4): MonkeyPatch, Tests for Azure credential factory., Legacy auth helper should delegate to the centralized credential factory., test_get_azure_credential_initializes_default_credential()

### Community 129 - ".__init__"
Cohesion: 0.40
Nodes (4): Secret-safe Azure credential configuration summary., Return display lines without credential values., RedactedAzureCredentialSummary, _yes_no()

### Community 130 - ".get_token"
Cohesion: 0.40
Nodes (5): detect_delivery_detail_leakage(), Return whether a change-intent field exposes delivery-only metadata., _remove_delivery_detail_sentences(), _restore_terminal_punctuation(), _strip_trailing_delivery_clause()

### Community 131 - "test_smoke_azure_credentials.py"
Cohesion: 0.50
Nodes (4): Any, Tests for the Azure credential smoke script., test_smoke_azure_credentials_default_does_not_call_network(), test_smoke_azure_credentials_help_works_without_azure_access()

### Community 132 - "test_normalize_endpoint_returns_expected_summary"
Cohesion: 0.67
Nodes (3): MonkeyPatch, Normalize endpoint should return safe summary with canonical path., test_normalize_endpoint_returns_expected_summary()

## Knowledge Gaps
- **77 isolated node(s):** `.`, `dod`, `image_distro`, `env`, `ado-dod-agent` (+72 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `test_dod_runs_artifact_api.py` to `test_credentials.py`, `AzureDevOpsBaseClient`, `config.py`, `Settings`, `dod_runs.py`, `collect_raw_metadata`, `FakeStore`, `CosmosArtifactStore`, `CombinedLlmOutputs`, `langsmith_tracing.py`, `LocalJsonStore`, `evaluate_rules.py`, `canonical.py`, `run_dod_workflow`, `AzureFoundryChatClient`, `Any`, `redaction.py`, `assess_evidence_quality`, `smoke_cosmos.py`, `validate_service_now_payload.py`, `_required_cosmos_config`, `normalize_raw_metadata.py`, `run_dod_agent`, `cosmos_artifact_store.py`, `test_llm_generator.py`, `run_dod_agent.py`, `test_dod_graph_advanced_nodes.py`, `build_evidence_buckets.py`, `init_cosmos.py`, `test_cosmos_document_type.py`, `._get_container`, `.output_path`, `smoke_keyvault_config.py`, `test_validated_output_models.py`, `.settings_customise_sources`, `test_dod_runs_rule_evaluation_api.py`, `resolve_runtime_config`, `validate_env.py`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Why does `LocalJsonStore` connect `Any` to `test_dod_runs_rule_evaluation_api.py`, `dod_runs.py`, `collect_raw_metadata`, `build_evidence_buckets.py`, `test_dod_runs_artifact_api.py`, `assess_evidence_quality`, `nodes.py`, `.load_artifact`, `validate_service_now_payload.py`, `LocalJsonStore`, `generate_service_now_fields.py`, `run_dod_agent`, `test_validated_output_models.py`, `evaluate_rules.py`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `langsmith_tracing.py` to `config.py`, `dod_runs.py`, `collect_raw_metadata`, `smoke_ado_auth.py`, `DodGraphState`, `RuleResult`, `nodes.py`, `dod_deployment_graph.py`, `LocalJsonStore`, `evaluate_rules.py`, `Any`, `assess_evidence_quality`, `validate_service_now_payload.py`, `smoke_llm_access.py`, `normalize_raw_metadata.py`, `run_dod_agent`, `cosmos_artifact_store.py`, `generator.py`, `generate_service_now_fields.py`, `run_dod_agent.py`, `test_dod_graph_advanced_nodes.py`, `build_evidence_buckets.py`, `test_dod_runs_artifact_api.py`, `.output_path`, `resolve_runtime_config`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `Settings` (e.g. with `AzureDevOpsBaseClient` and `AzureDevOpsClientConfig`) actually correct?**
  _`Settings` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `LocalJsonStore` (e.g. with `Settings` and `test_local_json_backend_selects_local_store()`) actually correct?**
  _`LocalJsonStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `CosmosArtifactStore` (e.g. with `Settings` and `run_container_readiness()`) actually correct?**
  _`CosmosArtifactStore` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `.`, `dod`, `image_distro` to the rest of the system?**
  _77 weakly-connected nodes found - possible documentation gaps or missing edges._