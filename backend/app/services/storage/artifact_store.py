"""Common artifact storage contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class ArtifactStore(Protocol):
    """Storage contract shared by local JSON and Cosmos artifact stores."""

    def ensure_run_dirs(self, build_id: int) -> Path:
        ...

    def save_json(self, relative_path: str, payload: Any) -> str:
        ...

    def save_artifact(
        self,
        run_id: str,
        build_id: int,
        artifact_type: str,
        content: dict[str, Any],
    ) -> str:
        ...

    def load_artifact(self, run_id: str, artifact_type: str) -> dict[str, Any]:
        ...

    def load_artifact_by_build_id(self, build_id: int, artifact_type: str) -> dict[str, Any]:
        ...

    def list_artifacts(self, run_id: str) -> list[str]:
        ...

    def save_run_summary(self, run_id: str, build_id: int, content: dict[str, Any]) -> str:
        ...

    def load_run_summary(self, run_id: str) -> dict[str, Any]:
        ...
