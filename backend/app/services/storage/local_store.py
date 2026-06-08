"""Local JSON storage abstraction for raw metadata artifacts."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from backend.app.utils.config import Settings, get_settings


def _make_json_safe(value: Any) -> Any:
    """Recursively convert values into JSON-serializable equivalents."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    return str(value)


class LocalJsonStore:
    """File-backed JSON storage for raw collection artifacts."""

    def __init__(self, settings: Settings | None = None) -> None:
        resolved_settings = settings or get_settings()
        self._base_dir = Path(resolved_settings.DATA_DIR)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_run_dirs(self, build_id: int) -> Path:
        """Ensure and return raw output directory for a build id."""

        path = self._base_dir / "raw" / str(build_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def raw_path(self, build_id: int, filename: str) -> str:
        """Return canonical local path for a raw artifact file."""

        return str(self._base_dir / "raw" / str(build_id) / filename)

    def normalized_path(self, build_id: int, filename: str) -> str:
        """Return canonical local path for a normalized artifact file."""

        return str(self._base_dir / "normalized" / str(build_id) / filename)

    def evidence_path(self, build_id: int, filename: str) -> str:
        """Return canonical local path for an evidence artifact file."""

        return str(self._base_dir / "evidence" / str(build_id) / filename)

    def output_path(self, build_id: int, filename: str) -> str:
        """Return canonical local path for a generated output artifact file."""

        return str(self._base_dir / "output" / str(build_id) / filename)

    def save_json(self, relative_path: str, payload: Any) -> str:
        """Save payload as UTF-8 pretty JSON and return absolute path string."""

        target_path = self._base_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        safe_payload = _make_json_safe(payload)
        target_path.write_text(
            json.dumps(safe_payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(target_path)

    def load_json(self, relative_path: str) -> Any:
        """Load a UTF-8 JSON document from storage."""

        target_path = self._base_dir / relative_path
        return json.loads(target_path.read_text(encoding="utf-8"))

    def save_normalized_json(self, build_id: int, filename: str, payload: Any) -> str:
        """Save normalized payload under `data/normalized/{build_id}`."""

        return self.save_json(f"normalized/{build_id}/{filename}", payload)

    def save_evidence_json(self, build_id: int, filename: str, payload: Any) -> str:
        """Save evidence payload under `data/evidence/{build_id}`."""

        return self.save_json(f"evidence/{build_id}/{filename}", payload)

    def save_output_json(self, build_id: int, filename: str, payload: Any) -> str:
        """Save generated output payload under `data/output/{build_id}`."""

        return self.save_json(f"output/{build_id}/{filename}", payload)

    def save_validated_output_json(self, build_id: int, payload: Any) -> str:
        """Save the full Phase 6 validated output artifact."""

        return self.save_output_json(build_id, "validated_output.json", payload)

    def save_service_now_payload_json(self, build_id: int, payload: Any) -> str:
        """Save the flat ServiceNow-ready payload artifact."""

        return self.save_output_json(build_id, "service_now_payload.json", payload)

    def save_confidence_json(self, build_id: int, payload: Any) -> str:
        """Save the Phase 6 confidence score artifact."""

        return self.save_output_json(build_id, "confidence.json", payload)

    def traceability_report_path(self, build_id: int) -> str:
        """Return canonical local path for a Phase R3 traceability report."""

        return self.output_path(build_id, "traceability_report.json")

    def rule_evaluation_path(self, build_id: int) -> str:
        """Return canonical local path for a Phase 9 rule evaluation artifact."""

        return self.output_path(build_id, "rule_evaluation.json")

    def run_summary_path(self, build_id: int) -> str:
        """Return canonical local path for a Phase 7A run summary."""

        return self.output_path(build_id, "run_summary.json")

    def routing_decisions_path(self, build_id: int) -> str:
        """Return canonical local path for a Phase 7B routing decisions artifact."""

        return self.output_path(build_id, "routing_decisions.json")

    def save_routing_decisions_json(self, build_id: int, payload: Any) -> str:
        """Save the Phase 7B routing decisions artifact."""

        return self.save_output_json(build_id, "routing_decisions.json", payload)

    def save_traceability_report_json(self, build_id: int, payload: Any) -> str:
        """Save the Phase R3 traceability report artifact."""

        return self.save_output_json(build_id, "traceability_report.json", payload)

    def save_rule_evaluation_json(self, build_id: int, payload: Any) -> str:
        """Save the Phase 9 rule evaluation artifact."""

        return self.save_output_json(build_id, "rule_evaluation.json", payload)

    def save_run_summary_json(self, build_id: int, payload: Any) -> str:
        """Save the Phase 7A orchestration run summary artifact."""

        return self.save_output_json(build_id, "run_summary.json", payload)

    def load_raw_bundle(self, build_id: int) -> dict[str, Any]:
        """Load raw bundle payload for a build id."""

        payload = self.load_json(f"raw/{build_id}/raw_bundle.json")
        return payload if isinstance(payload, dict) else {}

    def load_canonical(self, build_id: int) -> dict[str, Any]:
        """Load canonical payload for a build id."""

        payload = self.load_json(f"normalized/{build_id}/canonical.json")
        return payload if isinstance(payload, dict) else {}

    def load_evidence_bundle(self, build_id: int) -> dict[str, Any]:
        """Load Phase 4 evidence bundle payload for a build id."""

        payload = self.load_json(f"evidence/{build_id}/evidence_bundle.json")
        return payload if isinstance(payload, dict) else {}

    def load_evidence_bucket(self, build_id: int, bucket_filename: str) -> dict[str, Any]:
        """Load one Phase 4 evidence bucket payload for a build id."""

        payload = self.load_json(f"evidence/{build_id}/{bucket_filename}")
        return payload if isinstance(payload, dict) else {}

    def load_llm_outputs(self, build_id: int) -> dict[str, Any]:
        """Load Phase 5B combined LLM outputs for a build id."""

        payload = self.load_json(f"output/{build_id}/llm_outputs.json")
        return payload if isinstance(payload, dict) else {}

    def load_service_now_payload(self, build_id: int) -> dict[str, Any]:
        """Load the flat ServiceNow-ready payload for a build id."""

        payload = self.load_json(f"output/{build_id}/service_now_payload.json")
        return payload if isinstance(payload, dict) else {}

    def load_confidence(self, build_id: int) -> dict[str, Any]:
        """Load confidence artifact for a build id."""

        payload = self.load_json(f"output/{build_id}/confidence.json")
        return payload if isinstance(payload, dict) else {}

    def load_traceability_report(self, build_id: int) -> dict[str, Any]:
        """Load traceability report artifact for a build id."""

        payload = self.load_json(f"output/{build_id}/traceability_report.json")
        return payload if isinstance(payload, dict) else {}

    def load_validated_output(self, build_id: int) -> dict[str, Any]:
        """Load validated output artifact for a build id."""

        payload = self.load_json(f"output/{build_id}/validated_output.json")
        return payload if isinstance(payload, dict) else {}

    def load_run_summary(self, build_id: int) -> dict[str, Any]:
        """Load Phase 7A run summary payload for a build id."""

        payload = self.load_json(f"output/{build_id}/run_summary.json")
        return payload if isinstance(payload, dict) else {}

    def load_routing_decisions(self, build_id: int) -> dict[str, Any]:
        """Load Phase 7B routing decisions payload for a build id."""

        payload = self.load_json(f"output/{build_id}/routing_decisions.json")
        return payload if isinstance(payload, dict) else {}

    def load_rule_evaluation(self, build_id: int) -> dict[str, Any]:
        """Load Phase 9 rule evaluation payload for a build id."""

        payload = self.load_json(f"output/{build_id}/rule_evaluation.json")
        return payload if isinstance(payload, dict) else {}

    def artifact_exists(self, build_id: int, artifact_name: str) -> bool:
        """Return whether an output artifact exists for a build id."""

        return (self._base_dir / "output" / str(build_id) / artifact_name).exists()

