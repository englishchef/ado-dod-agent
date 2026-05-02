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

    def load_raw_bundle(self, build_id: int) -> dict[str, Any]:
        """Load raw bundle payload for a build id."""

        payload = self.load_json(f"raw/{build_id}/raw_bundle.json")
        return payload if isinstance(payload, dict) else {}

    def load_canonical(self, build_id: int) -> dict[str, Any]:
        """Load canonical payload for a build id."""

        payload = self.load_json(f"normalized/{build_id}/canonical.json")
        return payload if isinstance(payload, dict) else {}

