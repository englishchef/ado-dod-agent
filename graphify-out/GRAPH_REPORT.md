# Graph Report - ado-dod-agent  (2026-07-17)

## Corpus Check
- 262 files · ~97,511 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2666 nodes · 6990 edges · 131 communities (117 shown, 14 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 230 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c04b6687`
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

## God Nodes (most connected - your core abstractions)
1. `Settings` - 183 edges
2. `LocalJsonStore` - 93 edges
3. `get_settings()` - 66 edges
4. `CosmosArtifactStore` - 65 edges
5. `build_evidence_bundle()` - 45 edges
6. `_TimelineDescendant` - 42 edges
7. `validate_bucket_3_fields()` - 39 edges
8. `_complete_canonical()` - 37 edges
9. `DodGraphState` - 35 edges
10. `collect_raw_metadata()` - 35 edges

## Surprising Connections (you probably didn't know these)
- `main()` --indirect_call--> `AzureCredentialConfigError`  [INFERRED]
  scripts/smoke_azure_credentials.py → backend/app/core/azure_credentials.py
- `test_client_secret_mode_requires_all_fields()` --calls--> `validate_azure_credential_config()`  [EXTRACTED]
  tests/unit/test_azure_credentials.py → backend/app/core/azure_credentials.py
- `main()` --indirect_call--> `EnterpriseConfigError`  [INFERRED]
  scripts/smoke_enterprise_runtime_config.py → backend/app/core/enterprise_config.py
- `test_validate_langgraph_assistant_id_dod()` --calls--> `validate_langgraph_api_key_config()`  [EXTRACTED]
  tests/unit/test_langgraph_api_key.py → backend/app/core/langgraph_api_key.py
- `test_redacted_summary_never_includes_api_key_value()` --calls--> `get_redacted_langgraph_api_key_summary()`  [EXTRACTED]
  tests/unit/test_langgraph_api_key.py → backend/app/core/langgraph_api_key.py

## Import Cycles
- None detected.

## Communities (131 total, 14 thin omitted)

### Community 0 - "builder.py"
Cohesion: 0.14
Nodes (17): DodRunSummary, BaseModel, Phase 7A orchestration run summary models., Structured non-sensitive issue captured during orchestration., Persisted summary for one end-to-end DoD agent run., RunIssue, Any, Tests for shared DoD run contract models. (+9 more)

### Community 1 - "AzureDevOpsBaseClient"
Cohesion: 0.07
Nodes (39): AzureDevOpsBaseClient, AzureDevOpsClientConfig, Shared Azure DevOps REST client foundation., Close owned HTTP client resources., Configuration for Azure DevOps REST API access., Project-scoped Azure DevOps base URL., Reusable async Azure DevOps REST client., AzureDevOpsBuildClient (+31 more)

### Community 2 - "config.py"
Cohesion: 0.07
Nodes (34): AzureDevOpsTokenProvider, AzureIdentityAdoTokenProvider, Azure DevOps token provider implementations., Token provider backed by Azure Identity for Entra-authenticated ADO calls., Return bearer-token headers for synchronous call sites., Return bearer-token headers for asynchronous call sites., Backward-compatible alias for historical class naming., build_azure_credential() (+26 more)

### Community 3 - "Settings"
Cohesion: 0.08
Nodes (43): Validate credential config without creating a credential or printing values., validate_azure_credential_config(), Return safe validation errors/warnings for the optional Key Vault pointer., validate_agent_config_pointer(), get_redacted_langgraph_api_key_summary(), LangGraph API key retrieval for external invocation helpers., Validate LangGraph API-key Key Vault pointer without fetching the secret., Return a safe summary that never includes the API key value. (+35 more)

### Community 4 - "raw_metadata.py"
Cohesion: 0.15
Nodes (32): Models package exports., BuildEvidenceResponse, HealthResponse, NormalizeRawResponse, BaseModel, Output schemas returned by API endpoints., Service liveness payload., Placeholder run generation response for Phase 0. (+24 more)

### Community 5 - "dod_runs.py"
Cohesion: 0.07
Nodes (51): ApiIssue, ArtifactResponse, GenerateRunRequest, GenerateRunResponse, BaseModel, API request/response models for Phase 8 pipeline-facing endpoints., Request body for running the DoD agent workflow., API-safe issue model. (+43 more)

### Community 6 - "collect_raw_metadata"
Cohesion: 0.14
Nodes (25): CollectRawInput, GenerateRunInput, Input schemas for API operations., Phase-2 request model for raw metadata collection., Phase-0 placeholder payload for generate-run orchestration., collect_raw(), Collect raw build metadata and persist local artifacts., _as_collect_input() (+17 more)

### Community 7 - "smoke_ado_auth.py"
Cohesion: 0.09
Nodes (27): lifespan(), FastAPI entrypoint for ado-dod-agent., Initialize runtime resources at startup., Application readiness response., ReadyResponse, health(), _is_configured(), Depends (+19 more)

### Community 8 - "dod_contracts.py"
Cohesion: 0.11
Nodes (33): _derive_rule_evaluation_summary(), _dict_or_empty(), DoDRuleEvaluationSummary, DoDRunArtifactPaths, DoDRunError, DoDRunInput, DoDRunWarning, _int_or_default() (+25 more)

### Community 9 - "FakeStore"
Cohesion: 0.11
Nodes (19): _base_state(), _fake_llm_outputs(), _fake_validated(), FakeModel, FakeStore, Any, MonkeyPatch, Path (+11 more)

### Community 10 - "DodGraphState"
Cohesion: 0.12
Nodes (35): LangGraph workflow package., build_evidence_buckets_node(), generate_llm_outputs_node(), _generate_llm_outputs_once(), _merge_artifact_paths(), _model_or_none(), normalize_canonical_node(), _on_bucket_retry() (+27 more)

### Community 11 - "test_bucket_prompts.py"
Cohesion: 0.07
Nodes (41): build_prompt(), Any, Prompt builder for Phase 5B change intent fields., Build the bucket 1 prompt from deterministic evidence only., _strategy_guidance(), build_prompt(), Any, Prompt builder for Phase 5B execution and validation fields. (+33 more)

### Community 12 - "get_azure_credential"
Cohesion: 0.18
Nodes (21): AzureCredentialConfigError, get_azure_credential(), get_azure_credential_mode(), ValueError, Raised when Azure credential configuration is invalid., Return the configured Azure SDK credential without logging secret values., Return configured Azure credential mode, defaulting to local-compatible default., FakeClientSecretCredential (+13 more)

### Community 13 - "output_repair.py"
Cohesion: 0.11
Nodes (47): format_backout_minutes(), is_non_deployment_stage_name(), Return whether a stage is explicitly build, scan, approval, artifact, or test-on, Format rounded minutes without seconds or false precision., _backout_steps_for_actions(), _best_lower_environment_stage_duration(), _brief_backout_mitigation(), bucket_3_claim_evidence_text() (+39 more)

### Community 14 - "RuleResult"
Cohesion: 0.12
Nodes (34): ConfidenceAdjustment, BaseModel, Deterministic rule evaluation models for Phase 9., Base config for rule evaluation payloads., RuleBaseModel, RuleEvaluation, RuleEvaluationSummary, RuleResult (+26 more)

### Community 15 - "nodes.py"
Cohesion: 0.13
Nodes (33): assemble_run_result_node(), _coerce_build_id(), _coerce_float(), _coerce_str(), collect_raw_metadata_node(), _collector_issue(), _duration_ms(), evaluate_rules_node() (+25 more)

### Community 16 - "select_prompt_strategy"
Cohesion: 0.11
Nodes (36): EvidenceQualityAssessment, PromptStrategySelection, BaseModel, Deterministic routing models for Phase 7B orchestration., One audited routing decision made by the graph., Quality assessment for prompt-ready evidence buckets., Selected prompt strategies for each bucket., Risk tier assessment derived from deterministic evidence. (+28 more)

### Community 17 - "test_evidence_builder.py"
Cohesion: 0.18
Nodes (30): build_evidence_bundle(), Build all evidence buckets from canonical normalized input., _complete_canonical(), _contains_raw_ref(), _deployment_stage(), _deployment_task(), Any, Tests for deterministic Phase-4 evidence bucket builder. (+22 more)

### Community 18 - "CosmosArtifactStore"
Cohesion: 0.17
Nodes (5): CosmosArtifactStore, Any, Load run summary by run id or by build id for endpoint compatibility., Cosmos-backed artifact store for local emulator and enterprise runtime., Load the newest matching artifact for a build id.

### Community 19 - "dod_deployment_graph.py"
Cohesion: 0.10
Nodes (25): make_graph_dod(), Any, LangGraph deployment adapter for the DoD agent., Compile the enterprise LangGraph deployment graph for the DoD assistant., _run_dod_node(), DoDGraphState, normalize_dod_input(), TypedDict (+17 more)

### Community 20 - "canonical.py"
Cohesion: 0.08
Nodes (67): CanonicalScanSummary, _as_dict(), _as_float(), _as_int(), _as_list(), _as_str(), build_canonical_summary(), _contains_any() (+59 more)

### Community 21 - "CombinedLlmOutputs"
Cohesion: 0.13
Nodes (27): Bucket1GeneratedOutput, Bucket2GeneratedOutput, Bucket3GeneratedOutput, CombinedLlmOutputs, LlmModelMetadata, LlmOutputBaseModel, BaseModel, Pydantic models for Phase 5B generated ServiceNow field drafts. (+19 more)

### Community 22 - "langsmith_tracing.py"
Cohesion: 0.13
Nodes (27): Observability helpers for DoD agent tracing., build_run_metadata(), _duration_ms(), get_trace_mode(), _langsmith_client(), _phase_durations(), _project_name(), Any (+19 more)

### Community 23 - "LocalJsonStore"
Cohesion: 0.08
Nodes (30): Local JSON storage abstraction for raw metadata artifacts., Storage backend selection for DoD artifacts., Runtime configuration loaded from environment variables., Any, Tests for the common artifact store contract., test_local_json_store_satisfies_artifact_store_contract(), Path, Tests for local JSON storage abstraction. (+22 more)

### Community 24 - "load_agent_config_from_key_vault"
Cohesion: 0.12
Nodes (30): create_default_azure_credential(), EnterpriseConfigError, load_agent_config_from_key_vault(), parse_agent_config_json(), _present_value(), Any, ValueError, Enterprise runtime config resolution for the DoD agent. (+22 more)

### Community 25 - "DodRunSummary"
Cohesion: 0.36
Nodes (14): Any, MonkeyPatch, Tests for Phase 8 /api/v1/runs/generate endpoint., _request(), _summary(), test_generate_endpoint_accepts_x_correlation_id_header(), test_generate_endpoint_body_correlation_id_overrides_header(), test_generate_endpoint_calls_run_dod_agent() (+6 more)

### Community 26 - "output_validator.py"
Cohesion: 0.19
Nodes (30): ValidationIssue, detect_delivery_detail_leakage(), longest_contiguous_word_overlap(), Return whether a change-intent field exposes delivery-only metadata., Return the longest contiguous word run shared by both values., _as_dict(), _backout_derivation_issues(), _bucket() (+22 more)

### Community 27 - "service.py"
Cohesion: 0.14
Nodes (27): TraceabilityReport, BucketValidationResult, ConfidenceScore, BaseModel, Validated Phase 6 ServiceNow-ready output models., Base config for validated output payloads., ServiceNowPayload, ValidatedDodOutput (+19 more)

### Community 28 - "extract_json_object"
Cohesion: 0.10
Nodes (28): _candidate_json_strings(), _extract_balanced_object(), extract_json_object(), JsonParseError, Any, Defensive JSON object extraction for LLM responses., Raised when an LLM response cannot be parsed as one JSON object., Extract and parse a JSON object from raw LLM text. (+20 more)

### Community 29 - "validate_bucket_3_fields"
Cohesion: 0.19
Nodes (37): Normalize Bucket 3 fields to concise, evidence-grounded ServiceNow text., repair_bucket_3_fields(), Validate concise, evidence-grounded backout and risk field intent., validate_bucket_3_fields(), test_validator_flags_legacy_empty_activity_rejection_and_incomplete_traversal(), _assert_narrative_risk_format(), _evidence(), _labeled_risk_text() (+29 more)

### Community 30 - "evaluate_rules.py"
Cohesion: 0.13
Nodes (28): _build_parser(), build_summary(), format_summary(), _load_optional(), _load_required(), main(), Any, ArgumentParser (+20 more)

### Community 31 - "canonical.py"
Cohesion: 0.17
Nodes (33): CanonicalArtifact, CanonicalBaseModel, CanonicalCommit, CanonicalDodDocument, CanonicalPullRequest, CanonicalTestResult, CanonicalTestRun, CanonicalTestSummary (+25 more)

### Community 32 - "render_workflow_ascii.py"
Cohesion: 0.16
Nodes (27): build_ascii_from_workflow(), _build_parser(), _conditional_edges_by_source(), _continue_target(), _display_node(), _edge_with_label(), GraphEdge, _linear_chain() (+19 more)

### Community 33 - "get_langgraph_api_key"
Cohesion: 0.36
Nodes (8): Validate key names and required enterprise config shape without values., validate_key_vault_config_contract(), Tests for the DoD Key Vault JSON config contract., test_agent_config_contract_rejects_actual_langgraph_api_key(), test_contract_rejects_artifact_payload_keys(), test_contract_requires_expected_top_level_keys(), test_enterprise_contract_requires_default_credential_for_sample(), test_valid_enterprise_key_vault_contract_passes()

### Community 34 - "run_dod_workflow"
Cohesion: 0.24
Nodes (26): Any, Run the Phase 7A workflow and return final graph state., run_dod_workflow(), _input(), _patch_common(), Any, MonkeyPatch, Tests for Phase 7B advanced workflow routing. (+18 more)

### Community 35 - "smoke_enterprise_runtime_config.py"
Cohesion: 0.16
Nodes (35): EvidenceSourceRef, _bucket_3_text_sources(), build_bucket_1_change_intent(), build_bucket_2_execution_validation(), build_bucket_3_rollback_risk(), _build_resiliency_evidence(), clean_text(), _collect_matching_evidence() (+27 more)

### Community 36 - "AzureFoundryChatClient"
Cohesion: 0.19
Nodes (20): AzureFoundryChatClient, LlmClientError, Raised when local LLM smoke validation cannot be completed safely., Small Entra-only wrapper around LangChain AzureChatOpenAI., DummyModel, DummyResponse, Any, Exception (+12 more)

### Community 37 - "Any"
Cohesion: 0.05
Nodes (38): LocalJsonStore, _make_json_safe(), Any, Load one artifact by build id using local output filenames., List artifact types referenced by a local run summary., Save run summary through the shared ArtifactStore contract., Recursively convert values into JSON-serializable equivalents., Load run summary by build id or, for ArtifactStore, by run id. (+30 more)

### Community 38 - "validate_pipeline_config"
Cohesion: 0.16
Nodes (24): _build_parser(), _contains_container_apps_reference(), main(), PipelineConfigValidation, ArgumentParser, Path, Static validation for the DoD enterprise pipeline configuration., Safe static validation result for the .pipelines folder. (+16 more)

### Community 39 - "score_confidence"
Cohesion: 0.20
Nodes (23): _adjust(), _as_dict(), _bucket(), _clamp(), _deterministic_bucket_score(), _has_acceptance_or_business_value(), _model_confidence(), Any (+15 more)

### Community 40 - "servicenow_formatter.py"
Cohesion: 0.18
Nodes (21): FieldTraceability, BaseModel, Traceability report models for ServiceNow payload generation., Base config for traceability payloads., TraceabilityBaseModel, build_traceability_report(), _dict_list(), _optional_dict() (+13 more)

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
Cohesion: 0.15
Nodes (19): get_storage_store(), Return the configured artifact store., _build_parser(), load_env_local(), Deprecated wrapper for local Cosmos artifact smoke testing., main(), _missing_full_run_config(), ArgumentParser (+11 more)

### Community 47 - "validate_service_now_payload.py"
Cohesion: 0.15
Nodes (27): _build_parser(), build_summary(), format_summary(), _load_evidence_bundle(), _load_llm_outputs(), main(), persist_outputs(), Any (+19 more)

### Community 48 - "clean_servicenow_field_text"
Cohesion: 0.14
Nodes (22): clean_servicenow_field_text(), format_service_now_payload(), normalize_servicenow_whitespace(), Clean one ServiceNow field without changing business meaning., Remove raw/internal reference tokens from field text., Normalize whitespace while preserving meaningful numbered lists., Remove markdown code fences from generated text., Return a clean ServiceNow payload with exactly the eight supported fields. (+14 more)

### Community 49 - "_required_cosmos_config"
Cohesion: 0.18
Nodes (14): _required_cosmos_config(), FakeContainer, Any, Tests for the official Cosmos artifact store without an emulator., _settings(), test_cosmos_config_default_credential_does_not_require_key(), test_cosmos_config_requires_key_for_key_modes(), test_save_load_and_list_with_mocked_container() (+6 more)

### Community 50 - ".save_output_json"
Cohesion: 0.11
Nodes (24): _classify_activity_text(), classify_deployment_action(), deployment_action_kind(), DeploymentActionClassification, display_application_name(), _input_values(), is_deployment_activity_name(), is_explicit_deployment_container_name() (+16 more)

### Community 51 - "test_output_validator.py"
Cohesion: 0.20
Nodes (19): detect_raw_reference_leakage(), Return whether text contains raw/internal evidence references., Validate that final ServiceNow fields do not expose internal evidence refs., validate_no_raw_reference_leakage(), evidence_bundle(), _issues(), Tests for deterministic Phase 6 output validation., test_absolute_no_risk_claim_is_flagged() (+11 more)

### Community 52 - "README.md"
Cohesion: 0.10
Nodes (19): Auth, Backend Layout, Backout Plan, Commands, Current Phase Scope, Endpoints, Phase 2 Raw Collection, Phase 3 Canonical Normalization (+11 more)

### Community 53 - "smoke_container_readiness.py"
Cohesion: 0.16
Nodes (19): DoDRunOutput, Structured output contract for DoD agent run summaries., graph_entrypoint(), load_langgraph_config(), main(), Any, Path, Smoke-check container readiness for LangGraph-native DoD deployment. (+11 more)

### Community 54 - "smoke_llm_access.py"
Cohesion: 0.16
Nodes (18): endpoint_host(), format_success_summary(), _is_azure_auth_failure(), _is_azure_http_failure(), main(), Exception, Smoke test Azure OpenAI-compatible Foundry model access using Entra ID., Return only the host portion of the configured endpoint. (+10 more)

### Community 55 - "normalize_raw_metadata.py"
Cohesion: 0.17
Nodes (11): ChatModel, _extract_content_part(), _is_placeholder(), _parse_json_object(), Any, Protocol, Azure OpenAI-compatible Foundry chat client using Entra ID auth., Minimal protocol for LangChain chat models used by this wrapper. (+3 more)

### Community 56 - "normalize_raw_bundle"
Cohesion: 0.67
Nodes (3): MonkeyPatch, Endpoint should return safe summary with output artifact paths., test_build_evidence_endpoint_returns_expected_summary()

### Community 57 - "run_dod_agent"
Cohesion: 0.12
Nodes (23): _parse_datetime(), Any, datetime, Service entry point for Phase 7A DoD agent orchestration., Run the DoD agent workflow and return the persisted run summary model., run_dod_agent(), Phase 7A orchestration service package., RuntimeError (+15 more)

### Community 58 - "cosmos_artifact_store.py"
Cohesion: 0.10
Nodes (14): _artifact_from_relative_path(), _artifact_type_from_filename(), _compat_uri(), _cosmos_uri(), _document_type_for_artifact(), _make_json_safe(), Path, Official Cosmos DB artifact store for DoD run artifacts. (+6 more)

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
Cohesion: 0.13
Nodes (49): ApplicationCandidateScoreEvidence, ApplicationResolutionEvidence, ArtifactEvidence, BackoutStepDerivationEvidence, BackoutStepIgnoredTaskEvidence, BackoutStepSourceTaskEvidence, BackoutTimeDerivationEvidence, ChangeIntentEvidence (+41 more)

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
Cohesion: 0.23
Nodes (15): _build_parser(), _evidence_quality_summary(), format_summary(), _load_routing_payload(), main(), _overall_confidence(), _prompt_strategy_summary(), Any (+7 more)

### Community 68 - "smoke_langgraph_health.py"
Cohesion: 0.07
Nodes (42): get_langgraph_api_key(), get_langgraph_api_key_config(), LangGraphApiKeyConfig, LangGraphApiKeyConfigError, _present_value(), Any, ValueError, Fetch the LangGraph API key string from Key Vault for external callers. (+34 more)

### Community 69 - "test_dod_graph_advanced_nodes.py"
Cohesion: 0.14
Nodes (24): assess_evidence_quality_node(), assess_risk_tier_node(), _decision_json(), _load_evidence_bundle_from_state(), Assess evidence quality for downstream routing., Assess risk tier for downstream prompt strategy and final routing., Select deterministic prompt strategies for each bucket., select_prompt_strategy_node() (+16 more)

### Community 70 - "evaluate_backout_rules"
Cohesion: 0.25
Nodes (12): evaluate_backout_rules(), Any, Backout plan quality rules., Evaluate backout plan quality rules., _risk_flags(), _rollback_supported(), _rule(), Tests for backout plan quality rules. (+4 more)

### Community 71 - "build_evidence_buckets.py"
Cohesion: 0.17
Nodes (15): build_evidence_summary(), Build safe summary payload for CLI/API responses., _build_parser(), format_summary(), main(), Any, ArgumentParser, Namespace (+7 more)

### Community 72 - "evaluate_rules"
Cohesion: 0.36
Nodes (12): evaluate_rules(), Any, Evaluate deterministic post-generation rules against existing artifacts., _clean_payload(), Tests for Phase 9 rule engine orchestration., _strong_evidence(), test_recommended_status_completed_when_no_rules(), test_recommended_status_completed_with_warnings() (+4 more)

### Community 73 - "ArtifactStore"
Cohesion: 0.18
Nodes (22): build_source_ref_map_entry(), _display_name(), _first_value(), _get_value(), normalize_source_ref(), Any, Friendly evidence source reference normalization., Return a friendly source reference and traceability map entry. (+14 more)

### Community 74 - "test_change_intent_field_separation.py"
Cohesion: 0.24
Nodes (11): Conservatively repair delivery leakage and repeated description sentences., repair_change_intent_fields(), _evidence_bundle(), _full_llm_output(), Focused tests for change-description and justification field separation., test_final_payload_repairs_fields_and_preserves_eight_field_contract(), test_repair_condenses_repeated_description_when_supported_rationale_remains(), test_repair_removes_delivery_metadata_and_retains_functional_change() (+3 more)

### Community 75 - "Enterprise Runtime Config"
Cohesion: 0.17
Nodes (11): Azure Credential, Confirmed Deployment Model, Enterprise Runtime Config, Key Vault JSON, LangGraph API Key Secret, LangGraph Platform Variables, LangSmith, Local Development (+3 more)

### Community 76 - "init_cosmos.py"
Cohesion: 0.16
Nodes (15): _build_parser(), load_env_local(), Deprecated wrapper for local Cosmos initialization., main(), ArgumentParser, Namespace, Path, Initialize the configured Cosmos artifact store database/container. (+7 more)

### Community 77 - "test_dod_runs_artifact_api.py"
Cohesion: 0.08
Nodes (33): Path, Return all data directories used by the pipeline lifecycle., Return official Cosmos auth mode, honoring deprecated local aliases., Return official Cosmos endpoint, honoring deprecated local aliases., Return official Cosmos key, honoring deprecated local aliases., Return official Cosmos database, honoring deprecated local aliases., Return official Cosmos container, honoring deprecated local aliases., Return whether Cosmos TLS verification is disabled. (+25 more)

### Community 78 - "Any"
Cohesion: 0.09
Nodes (22): collect_execution_context(), Any, Execution-context collector for timeline and artifact metadata., Collect timeline and artifacts with safe partial-failure behavior., collect_quality_context(), Any, Quality-context collector for test run/result metadata., Collect test runs and test results with partial-failure handling. (+14 more)

### Community 79 - ".load_artifact"
Cohesion: 0.20
Nodes (5): Return canonical local path for a Phase R3 traceability report., Return canonical local path for a Phase 9 rule evaluation artifact., Return canonical local path for a Phase 7A run summary., Return canonical local path for a Phase 7B routing decisions artifact., Return canonical local path for a generated output artifact file.

### Community 80 - "test_cosmos_document_type.py"
Cohesion: 0.31
Nodes (7): FakeContainer, Any, Tests for Cosmos document_type compatibility fields., _settings(), test_cosmos_artifact_write_includes_artifact_document_type(), test_cosmos_read_remains_compatible_when_document_type_missing(), test_cosmos_run_summary_write_includes_run_summary_document_type()

### Community 81 - "._get_container"
Cohesion: 0.17
Nodes (7): _content_from_document(), List artifact types stored for a run id., Delete one smoke-test artifact if it exists., Return the stable Cosmos document id for an artifact., Create the configured database and container if missing., Load one artifact by run id and artifact type., test_cosmos_document_id_and_partition_key()

### Community 82 - ".output_path"
Cohesion: 0.11
Nodes (20): Depends, Perform a minimal Azure DevOps Entra auth smoke check., smoke_ado_auth(), Build client config from application settings., _build_argument_parser(), build_safe_summary(), format_summary(), main() (+12 more)

### Community 83 - "smoke_azure_credentials.py"
Cohesion: 0.27
Nodes (20): CanonicalJob, CanonicalStage, CanonicalTask, _container_activity_items(), _is_completed_deployment_record(), _normalized_status(), Return every descendant in timeline order, with cycle protection and ancestry., _stage_rejection_reason() (+12 more)

### Community 84 - "smoke_keyvault_config.py"
Cohesion: 0.12
Nodes (11): AsyncClient, AzureDevOpsClientError, Exception, Raised when an Azure DevOps request fails., AdoTokenProvider, Protocol, Contract for components that produce Azure DevOps access tokens., Return authorization headers for Azure DevOps REST calls. (+3 more)

### Community 85 - "test_field_quality_rules.py"
Cohesion: 0.47
Nodes (9): _ids(), _payload(), Tests for ServiceNow field quality rules., test_duplicate_content_triggers_rule(), test_empty_field_triggers_rule(), test_generic_validation_plan_triggers_rule(), test_long_short_description_triggers_rule(), test_markdown_triggers_rule() (+1 more)

### Community 86 - "test_test_completeness_rules.py"
Cohesion: 0.42
Nodes (9): _empty_evidence(), Tests for Phase 9 test completeness scoring and rules., _rules(), test_failed_tests_trigger_rule(), test_missing_nonfunctional_evidence_triggers_rule(), test_no_test_evidence_triggers_no_automated_results(), test_score_is_low_when_no_test_or_validation_evidence_exists(), test_score_is_medium_when_tests_missing_but_validation_exists() (+1 more)

### Community 87 - "test_validate_service_now_payload_script.py"
Cohesion: 0.12
Nodes (21): get_redacted_credential_summary(), _managed_identity_client_id(), _present(), _present_value(), Any, Central Azure credential factory for DoD runtime integrations., Return a safe credential summary for logs and smoke scripts., Return user-assigned managed identity client id with canonical precedence. (+13 more)

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
Cohesion: 0.29
Nodes (8): assemble_service_now_payload(), Any, Assemble flat ServiceNow payloads from Phase 5B bucket outputs., Combine bucket outputs into exactly eight ServiceNow fields., Tests for final ServiceNow payload assembly., test_assembler_combines_bucket_outputs_into_exactly_8_fields(), test_assembler_removes_raw_internal_refs_from_final_payload(), _valid_payload_dict()

### Community 94 - "smoke_keyvault_config.py"
Cohesion: 0.24
Nodes (8): _build_parser(), main(), ArgumentParser, Live smoke-check for fetching the DoD agent JSON config secret., Any, Tests for enterprise runtime config smoke scripts., test_enterprise_runtime_smoke_default_mode_does_not_call_azure(), test_keyvault_config_smoke_imports_without_calling_azure()

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
Cohesion: 0.25
Nodes (8): correlation_id_middleware(), Response, Attach a correlation id to logs and responses for each request., clear_correlation_id(), Bind a correlation id to the current execution context., Remove request-scoped correlation id from current context., set_correlation_id(), Request

### Community 102 - ".get_test_results"
Cohesion: 0.40
Nodes (3): Any, Return test runs associated with a build., Return test results for a test run.

### Community 103 - "resolve_runtime_config"
Cohesion: 0.32
Nodes (7): is_tracing_enabled(), Return whether LangSmith tracing is explicitly enabled., Any, Tests for LangSmith tracing config aliases., test_langsmith_tracing_wins_over_tracing_enabled(), test_settings_applies_tracing_enabled_alias_when_canonical_absent(), test_tracing_enabled_alias_works_when_langsmith_tracing_absent()

### Community 104 - "DoD Run Contract"
Cohesion: 0.40
Nodes (4): DoD Run Contract, Input, Invocation Notes, Output

### Community 105 - "test_dockerignore_rules.py"
Cohesion: 0.60
Nodes (4): _dockerignore_lines(), Tests for Docker build context safety rules., test_dockerignore_does_not_exclude_langgraph_config(), test_dockerignore_excludes_secrets_and_generated_artifacts()

### Community 107 - "normalized_words"
Cohesion: 0.50
Nodes (5): normalized_words(), Return lowercase word tokens used by conservative overlap checks., Return a normalized word-sequence similarity score., _remove_repeated_justification_sentences(), sequence_similarity()

### Community 108 - "test_normalize_endpoint_returns_expected_summary"
Cohesion: 0.29
Nodes (4): Any, Query pull requests related to a commit., Get a single pull-request record., Get pull-request commit list.

### Community 109 - "validate_env.py"
Cohesion: 0.50
Nodes (4): _is_present(), main(), Validate Phase-0 environment configuration safely., Load settings and print presence/absence of key configuration values.

### Community 128 - "test_credentials.py"
Cohesion: 0.40
Nodes (4): MonkeyPatch, Tests for Azure credential factory., Legacy auth helper should delegate to the centralized credential factory., test_get_azure_credential_initializes_default_credential()

## Knowledge Gaps
- **76 isolated node(s):** `.`, `dod`, `image_distro`, `env`, `ado-dod-agent` (+71 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Settings` connect `test_dod_runs_artifact_api.py` to `test_credentials.py`, `AzureDevOpsBaseClient`, `config.py`, `.__init__`, `Settings`, `collect_raw_metadata`, `smoke_ado_auth.py`, `FakeStore`, `CosmosArtifactStore`, `canonical.py`, `CombinedLlmOutputs`, `LocalJsonStore`, `load_agent_config_from_key_vault`, `evaluate_rules.py`, `canonical.py`, `run_dod_workflow`, `AzureFoundryChatClient`, `Any`, `smoke_cosmos.py`, `validate_service_now_payload.py`, `_required_cosmos_config`, `smoke_llm_access.py`, `normalize_raw_metadata.py`, `run_dod_agent`, `cosmos_artifact_store.py`, `test_llm_generator.py`, `test_dod_graph_advanced_nodes.py`, `build_evidence_buckets.py`, `init_cosmos.py`, `test_cosmos_document_type.py`, `.output_path`, `smoke_keyvault_config.py`, `test_validated_output_models.py`, `.settings_customise_sources`, `test_dod_runs_rule_evaluation_api.py`, `resolve_runtime_config`?**
  _High betweenness centrality (0.168) - this node is a cross-community bridge._
- **Why does `LocalJsonStore` connect `Any` to `.__init__`, `test_dod_runs_rule_evaluation_api.py`, `dod_runs.py`, `collect_raw_metadata`, `build_evidence_buckets.py`, `DodGraphState`, `test_dod_runs_artifact_api.py`, `Any`, `nodes.py`, `.load_artifact`, `smoke_cosmos.py`, `validate_service_now_payload.py`, `canonical.py`, `LocalJsonStore`, `generate_service_now_fields.py`, `test_validated_output_models.py`, `evaluate_rules.py`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `smoke_ado_auth.py` to `.__init__`, `config.py`, `dod_runs.py`, `collect_raw_metadata`, `DodGraphState`, `RuleResult`, `nodes.py`, `canonical.py`, `langsmith_tracing.py`, `LocalJsonStore`, `evaluate_rules.py`, `smoke_cosmos.py`, `validate_service_now_payload.py`, `smoke_llm_access.py`, `normalize_raw_metadata.py`, `run_dod_agent`, `cosmos_artifact_store.py`, `generator.py`, `generate_service_now_fields.py`, `azure_foundry_client.py`, `run_dod_agent.py`, `build_evidence_buckets.py`, `test_dod_runs_artifact_api.py`, `Any`, `.output_path`, `resolve_runtime_config`, `validate_env.py`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `Settings` (e.g. with `AzureDevOpsBaseClient` and `AzureDevOpsClientConfig`) actually correct?**
  _`Settings` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `LocalJsonStore` (e.g. with `Settings` and `test_local_json_backend_selects_local_store()`) actually correct?**
  _`LocalJsonStore` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `CosmosArtifactStore` (e.g. with `Settings` and `run_container_readiness()`) actually correct?**
  _`CosmosArtifactStore` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `.`, `dod`, `image_distro` to the rest of the system?**
  _76 weakly-connected nodes found - possible documentation gaps or missing edges._