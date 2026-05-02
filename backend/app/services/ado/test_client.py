"""Azure DevOps Test API client."""

from __future__ import annotations

from typing import Any

from backend.app.services.ado.base import AzureDevOpsBaseClient


class AzureDevOpsTestClient(AzureDevOpsBaseClient):
    """Test run and result operations for build quality context."""

    async def get_test_runs(self, build_id: int) -> dict[str, Any]:
        """Return test runs associated with a build."""

        params = {
            "buildUri": f"vstfs:///Build/Build/{build_id}",
            "includeRunDetails": "true",
        }
        return await self._get("/_apis/test/runs", params=params)

    async def get_test_results(self, run_id: int, max_results: int = 200) -> dict[str, Any]:
        """Return test results for a test run."""

        params = {
            "$top": max_results,
        }
        return await self._get(f"/_apis/test/Runs/{run_id}/results", params=params)

