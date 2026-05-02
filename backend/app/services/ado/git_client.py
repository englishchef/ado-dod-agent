"""Azure DevOps Git API client."""

from __future__ import annotations

from typing import Any

from backend.app.services.ado.base import AzureDevOpsBaseClient


class AzureDevOpsGitClient(AzureDevOpsBaseClient):
    """Git and pull-request lookup operations for build context."""

    async def get_pull_requests_for_commit(
        self,
        repository_id: str,
        commit_id: str,
    ) -> dict[str, Any]:
        """Query pull requests related to a commit."""

        body = {
            "queries": [
                {
                    "type": "commit",
                    "items": [commit_id],
                }
            ]
        }
        return await self._post(
            f"/_apis/git/repositories/{repository_id}/pullrequestquery",
            body=body,
        )

    async def get_pull_request(
        self,
        repository_id: str,
        pull_request_id: int,
    ) -> dict[str, Any]:
        """Get a single pull-request record."""

        return await self._get(
            f"/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}"
        )

    async def get_pull_request_commits(
        self,
        repository_id: str,
        pull_request_id: int,
    ) -> dict[str, Any]:
        """Get pull-request commit list."""

        return await self._get(
            f"/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}/commits"
        )

