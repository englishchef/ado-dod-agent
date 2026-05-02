"""Azure DevOps work-item API client."""

from __future__ import annotations

from typing import Any

from backend.app.services.ado.base import AzureDevOpsBaseClient

DEFAULT_WORK_ITEM_FIELDS = [
    "System.Id",
    "System.WorkItemType",
    "System.Title",
    "System.State",
    "System.Reason",
    "System.AssignedTo",
    "System.CreatedBy",
    "System.ChangedBy",
    "System.AreaPath",
    "System.IterationPath",
    "System.Tags",
    "System.Description",
    "Microsoft.VSTS.Common.AcceptanceCriteria",
    "Microsoft.VSTS.Common.Priority",
    "Microsoft.VSTS.Common.BusinessValue",
]


class AzureDevOpsWorkItemClient(AzureDevOpsBaseClient):
    """Work-item operations for raw metadata hydration."""

    async def get_work_items_batch(
        self,
        work_item_ids: list[int],
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Hydrate work items in a batch request."""

        body = {
            "ids": work_item_ids,
            "fields": fields or DEFAULT_WORK_ITEM_FIELDS,
        }
        return await self._post("/_apis/wit/workitemsbatch", body=body)

