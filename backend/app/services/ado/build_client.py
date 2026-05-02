"""Azure DevOps build API client."""

from __future__ import annotations

from typing import Any

from backend.app.services.ado.base import AzureDevOpsBaseClient


class AzureDevOpsBuildClient(AzureDevOpsBaseClient):
    """Read-only build endpoints for smoke validation and future collectors."""

    async def get_build(self, build_id: int) -> dict[str, Any]:
        """Return a single build record."""

        return await self._get(f"/_apis/build/builds/{build_id}")

    async def get_build_timeline(self, build_id: int) -> dict[str, Any]:
        """Return timeline details for a build."""

        return await self._get(f"/_apis/build/builds/{build_id}/timeline")

    async def get_build_work_items_refs(self, build_id: int) -> dict[str, Any]:
        """Return linked work-item references for a build."""

        return await self._get(f"/_apis/build/builds/{build_id}/workitems")

    async def get_build_changes(self, build_id: int) -> dict[str, Any]:
        """Return source-control changes associated with a build."""

        return await self._get(f"/_apis/build/builds/{build_id}/changes")

    async def get_build_artifacts(self, build_id: int) -> dict[str, Any]:
        """Return build artifact metadata."""

        return await self._get(f"/_apis/build/builds/{build_id}/artifacts")

