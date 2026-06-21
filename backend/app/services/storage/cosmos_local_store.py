"""LOCAL-ONLY / DEV-ONLY Cosmos DB emulator artifact store.

This adapter is for local Cosmos DB emulator testing.
Do not merge this file into the org repo if the org repo already has an
enterprise Cosmos implementation. Use the org-owned Cosmos storage abstraction
in enterprise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.utils.config import Settings, get_settings

LOCAL_COSMOS_PARTITION_KEY = "/run_id"


class CosmosLocalStore:
    """Minimal local-only artifact store for the Cosmos DB emulator."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: Any | None = None
        self._database: Any | None = None
        self._container: Any | None = None

    def initialize(self) -> None:
        """Create the local emulator database and container if missing."""

        _ = self._get_container(create=True)

    def save_artifact(
        self,
        run_id: str,
        build_id: int,
        artifact_type: str,
        content: dict[str, Any],
    ) -> str:
        """Save or replace one local artifact document."""

        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        document_id = f"{run_id}:{artifact_type}"
        document = {
            "id": document_id,
            "run_id": run_id,
            "build_id": int(build_id),
            "artifact_type": artifact_type,
            "content": _make_json_safe(content),
            "created_at": now,
            "updated_at": now,
        }
        container = self._get_container(create=False)
        try:
            existing = container.read_item(item=document_id, partition_key=run_id)
            if isinstance(existing, dict) and existing.get("created_at"):
                document["created_at"] = existing["created_at"]
        except Exception:
            pass
        container.upsert_item(document)
        return _cosmos_uri(self.settings, run_id, artifact_type)

    def load_artifact(self, run_id: str, artifact_type: str) -> dict[str, Any]:
        """Load one artifact by run id and artifact type."""

        document_id = f"{run_id}:{artifact_type}"
        document = self._get_container(create=False).read_item(
            item=document_id,
            partition_key=run_id,
        )
        return _content_from_document(document)

    def load_artifact_by_build_id(self, build_id: int, artifact_type: str) -> dict[str, Any]:
        """Load the latest matching artifact for a build id."""

        query = (
            "SELECT * FROM c WHERE c.build_id = @build_id "
            "AND c.artifact_type = @artifact_type ORDER BY c.updated_at DESC"
        )
        parameters = [
            {"name": "@build_id", "value": int(build_id)},
            {"name": "@artifact_type", "value": artifact_type},
        ]
        items = list(
            self._get_container(create=False).query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        if not items:
            raise FileNotFoundError(
                f"Cosmos local artifact not found for build_id={build_id}, "
                f"artifact_type={artifact_type}."
            )
        return _content_from_document(items[0])

    def list_artifacts(self, run_id: str) -> list[str]:
        """List artifact types stored for a run id."""

        query = "SELECT c.artifact_type FROM c WHERE c.run_id = @run_id"
        parameters = [{"name": "@run_id", "value": run_id}]
        items = self._get_container(create=False).query_items(
            query=query,
            parameters=parameters,
            partition_key=run_id,
        )
        return sorted(
            str(item["artifact_type"])
            for item in items
            if isinstance(item, dict) and item.get("artifact_type")
        )

    def delete_artifact(self, run_id: str, artifact_type: str) -> None:
        """Delete one local smoke-test artifact if it exists."""

        document_id = f"{run_id}:{artifact_type}"
        try:
            self._get_container(create=False).delete_item(
                item=document_id,
                partition_key=run_id,
            )
        except Exception:
            return

    def ensure_run_dirs(self, build_id: int) -> Path:
        """Compatibility no-op for file-backed collection code."""

        return Path(f"cosmos_local/raw/{build_id}")

    def raw_path(self, build_id: int, filename: str) -> str:
        return _compat_uri(self.settings, build_id, "raw", filename)

    def normalized_path(self, build_id: int, filename: str) -> str:
        return _compat_uri(self.settings, build_id, "normalized", filename)

    def evidence_path(self, build_id: int, filename: str) -> str:
        return _compat_uri(self.settings, build_id, "evidence", filename)

    def output_path(self, build_id: int, filename: str) -> str:
        return _compat_uri(self.settings, build_id, "output", filename)

    def save_json(self, relative_path: str, payload: Any) -> str:
        build_id, artifact_type = _artifact_from_relative_path(relative_path)
        run_id = _run_id_from_payload(payload, build_id)
        content = payload if isinstance(payload, dict) else {"value": _make_json_safe(payload)}
        return self.save_artifact(run_id, build_id, artifact_type, content)

    def load_json(self, relative_path: str) -> Any:
        build_id, artifact_type = _artifact_from_relative_path(relative_path)
        return self.load_artifact_by_build_id(build_id, artifact_type)

    def save_normalized_json(self, build_id: int, filename: str, payload: Any) -> str:
        return self.save_json(f"normalized/{build_id}/{filename}", payload)

    def save_evidence_json(self, build_id: int, filename: str, payload: Any) -> str:
        return self.save_json(f"evidence/{build_id}/{filename}", payload)

    def save_output_json(self, build_id: int, filename: str, payload: Any) -> str:
        return self.save_json(f"output/{build_id}/{filename}", payload)

    def save_validated_output_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "validated_output.json", payload)

    def save_service_now_payload_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "service_now_payload.json", payload)

    def save_confidence_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "confidence.json", payload)

    def save_routing_decisions_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "routing_decisions.json", payload)

    def save_traceability_report_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "traceability_report.json", payload)

    def save_rule_evaluation_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "rule_evaluation.json", payload)

    def save_run_summary_json(self, build_id: int, payload: Any) -> str:
        return self.save_output_json(build_id, "run_summary.json", payload)

    def traceability_report_path(self, build_id: int) -> str:
        return self.output_path(build_id, "traceability_report.json")

    def rule_evaluation_path(self, build_id: int) -> str:
        return self.output_path(build_id, "rule_evaluation.json")

    def run_summary_path(self, build_id: int) -> str:
        return self.output_path(build_id, "run_summary.json")

    def routing_decisions_path(self, build_id: int) -> str:
        return self.output_path(build_id, "routing_decisions.json")

    def load_raw_bundle(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "raw_bundle")

    def load_canonical(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "canonical")

    def load_evidence_bundle(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "evidence_bundle")

    def load_evidence_bucket(self, build_id: int, bucket_filename: str) -> dict[str, Any]:
        artifact_type = _artifact_type_from_filename(bucket_filename)
        return self.load_artifact_by_build_id(build_id, artifact_type)

    def load_llm_outputs(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "llm_outputs")

    def load_service_now_payload(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "service_now_payload")

    def load_confidence(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "confidence")

    def load_traceability_report(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "traceability_report")

    def load_validated_output(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "validated_output")

    def load_run_summary(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "run_summary")

    def load_routing_decisions(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "routing_decisions")

    def load_rule_evaluation(self, build_id: int) -> dict[str, Any]:
        return self.load_artifact_by_build_id(build_id, "rule_evaluation")

    def artifact_exists(self, build_id: int, artifact_name: str) -> bool:
        try:
            self.load_artifact_by_build_id(build_id, _artifact_type_from_filename(artifact_name))
        except FileNotFoundError:
            return False
        return True

    def _get_container(self, *, create: bool) -> Any:
        if self._container is not None:
            return self._container

        endpoint, key = _required_cosmos_local_config(self.settings)
        try:
            from azure.cosmos import CosmosClient, PartitionKey  # type: ignore[import-untyped]
        except ModuleNotFoundError as exc:
            if exc.name != "azure":
                raise
            raise RuntimeError(
                "azure-cosmos is not installed. Install project dependencies before using "
                "DOD_STORAGE_BACKEND=cosmos_local."
            ) from exc

        client_kwargs: dict[str, Any] = {}
        if self.settings.COSMOS_LOCAL_DISABLE_TLS_VERIFY:
            client_kwargs["connection_verify"] = False
        self._client = CosmosClient(endpoint, credential=key, **client_kwargs)
        if create:
            self._database = self._client.create_database_if_not_exists(
                id=self.settings.COSMOS_LOCAL_DATABASE
            )
            self._container = self._database.create_container_if_not_exists(
                id=self.settings.COSMOS_LOCAL_CONTAINER,
                partition_key=PartitionKey(path=LOCAL_COSMOS_PARTITION_KEY),
            )
        else:
            self._database = self._client.get_database_client(
                self.settings.COSMOS_LOCAL_DATABASE
            )
            self._container = self._database.get_container_client(
                self.settings.COSMOS_LOCAL_CONTAINER
            )
        return self._container


def _required_cosmos_local_config(settings: Settings) -> tuple[str, str]:
    if settings.COSMOS_LOCAL_AUTH_MODE != "emulator_key":
        raise ValueError("COSMOS_LOCAL_AUTH_MODE must be emulator_key for cosmos_local.")
    endpoint = settings.COSMOS_LOCAL_ENDPOINT
    key = settings.COSMOS_LOCAL_KEY
    if not endpoint:
        raise ValueError("COSMOS_LOCAL_ENDPOINT is required for cosmos_local.")
    if not key or key == "<local-emulator-key-only>":
        raise ValueError("COSMOS_LOCAL_KEY is required for cosmos_local.")
    return endpoint, key


def _artifact_from_relative_path(relative_path: str) -> tuple[int, str]:
    parts = Path(relative_path).parts
    if len(parts) < 3:
        raise ValueError(f"Unsupported artifact path for cosmos_local: {relative_path}")
    try:
        build_id = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"Unsupported artifact path for cosmos_local: {relative_path}") from exc
    return build_id, _artifact_type_from_filename(parts[-1])


def _artifact_type_from_filename(filename: str) -> str:
    return Path(filename).stem


def _run_id_from_payload(payload: Any, build_id: int) -> str:
    if isinstance(payload, dict):
        candidate = payload.get("run_id") or payload.get("collection_run_id")
        if isinstance(candidate, str) and candidate:
            return candidate
    return f"build:{build_id}"


def _content_from_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        return {}
    content = document.get("content")
    return content if isinstance(content, dict) else {}


def _cosmos_uri(settings: Settings, run_id: str, artifact_type: str) -> str:
    return (
        f"cosmos-local://{settings.COSMOS_LOCAL_DATABASE}/"
        f"{settings.COSMOS_LOCAL_CONTAINER}/{run_id}/{artifact_type}"
    )


def _compat_uri(settings: Settings, build_id: int, area: str, filename: str) -> str:
    artifact_type = _artifact_type_from_filename(filename)
    return (
        f"cosmos-local://{settings.COSMOS_LOCAL_DATABASE}/"
        f"{settings.COSMOS_LOCAL_CONTAINER}/build:{build_id}/{area}/{artifact_type}"
    )


def _make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_make_json_safe(item) for item in value]
    return str(value)
