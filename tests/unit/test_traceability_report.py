"""Tests for ServiceNow traceability report generation."""

from __future__ import annotations

from backend.app.services.formatting.servicenow_formatter import build_traceability_report


def _llm_outputs() -> dict[str, object]:
    return {
        "bucket_1": {
            "evidence_used": ["work_item:12345", "commit:9f3a21b"],
        },
        "bucket_2": {
            "evidence_used": ["pipeline_task:Run_Functional_Tests"],
        },
        "bucket_3": {
            "evidence_used": ["artifact:drop"],
        },
    }


def _evidence_bundle() -> dict[str, object]:
    return {
        "bucket_3": {
            "environment_candidates": [
                {
                    "stage_name": "Deploy to UAT",
                    "normalized_environment": "UAT",
                    "selected": True,
                }
            ],
            "backout_time_derivation": {
                "calculation_method": "lower_environment_stage_duration",
                "selected_environment": "UAT",
                "selected_stage_name": "Deploy to UAT",
                "source_duration_seconds": 558,
                "final_estimate_minutes": 10,
            },
            "rejected_stages": [
                {"stage_name": "Production", "reason": "Production stages cannot be used."}
            ],
            "uat_deployment": {
                "activities": [
                    {"name": "Upgrade Solution AcctShutdownAcctCompromiseASAC"}
                ]
            },
            "application_resolution": {
                "selected_application": "contact-center-asac",
                "display_name": "Contact Center ASAC application",
                "selection_reason": "Repository and deployment evidence matched.",
                "candidate_scores": [],
            },
            "warnings": [],
        },
        "source_ref_map": {
            "work_item:12345": {
                "friendly_ref": "work_item:12345",
                "original_ref": "raw.work_items.value[0]",
                "source_type": "work_item",
                "display_name": "Change request",
            },
            "commit:9f3a21b": {
                "friendly_ref": "commit:9f3a21b",
                "original_ref": "raw.changes.value[3]",
                "source_type": "commit",
            },
            "pipeline_task:Run_Functional_Tests": {
                "friendly_ref": "pipeline_task:Run_Functional_Tests",
                "original_ref": "raw.timeline.records[10]",
                "source_type": "task",
            },
            "artifact:drop": {
                "friendly_ref": "artifact:drop",
                "original_ref": "raw.artifacts.value[0]",
                "source_type": "artifact",
            },
        }
    }


def test_builds_traceability_report_from_evidence_used() -> None:
    report = build_traceability_report(5, _llm_outputs(), _evidence_bundle())

    trace = report.field_traceability["change_description"]
    assert trace.evidence_used == ["work_item:12345", "commit:9f3a21b"]
    assert trace.friendly_refs == ["work_item:12345", "commit:9f3a21b"]


def test_maps_friendly_refs_to_original_refs() -> None:
    report = build_traceability_report(5, _llm_outputs(), _evidence_bundle())

    assert "raw.changes.value[3]" in report.field_traceability["justification"].original_refs
    assert (
        "raw.timeline.records[10]"
        in report.field_traceability["testing_performed"].original_refs
    )


def test_handles_missing_source_ref_map_gracefully() -> None:
    report = build_traceability_report(5, _llm_outputs(), {})

    assert report.warnings == ["source_ref_map_missing"]
    assert report.field_traceability["change_description"].friendly_refs == []


def test_traceability_report_serializes_to_json() -> None:
    payload = build_traceability_report(
        5,
        _llm_outputs(),
        _evidence_bundle(),
        source_llm_outputs_path="data/output/5/llm_outputs.json",
        source_evidence_bundle_path="data/evidence/5/evidence_bundle.json",
    ).model_dump(mode="json")

    assert payload["schema_version"] == "1.0"
    assert payload["source_llm_outputs_path"].endswith("llm_outputs.json")
    assert "field_traceability" in payload


def test_traceability_report_persists_bucket_3_derivations() -> None:
    report = build_traceability_report(5, _llm_outputs(), _evidence_bundle())

    assert report.backout_time_derivation is not None
    assert report.backout_time_derivation["source_duration_seconds"] == 558
    assert report.environment_candidates[0]["selected"] is True
    assert report.rejected_stages[0]["stage_name"] == "Production"
    assert report.deployment_activities_used[0]["name"].startswith("Upgrade Solution")
    assert report.application_resolution is not None
    assert report.application_resolution["selected_application"] == "contact-center-asac"
