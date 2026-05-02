"""Shared Azure DevOps REST client foundation."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx
from backend.app.services.auth.ado_token_provider import AdoTokenProvider
from backend.app.utils.config import Settings
from backend.app.utils.logging import get_logger

logger = get_logger(__name__)

_TRANSIENT_STATUS_CODES = {408, 429, 500, 502, 503, 504}


@dataclass(frozen=True, slots=True)
class AzureDevOpsClientConfig:
    """Configuration for Azure DevOps REST API access."""

    organization: str
    project: str
    api_version: str = "7.1"
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5

    @property
    def base_url(self) -> str:
        """Project-scoped Azure DevOps base URL."""

        return f"https://dev.azure.com/{self.organization}/{self.project}"

    @classmethod
    def from_settings(cls, settings: Settings) -> AzureDevOpsClientConfig:
        """Build client config from application settings."""

        if not settings.ADO_ORGANIZATION:
            raise ValueError("ADO_ORGANIZATION is required for Azure DevOps API calls.")
        if not settings.ADO_PROJECT:
            raise ValueError("ADO_PROJECT is required for Azure DevOps API calls.")
        return cls(
            organization=settings.ADO_ORGANIZATION,
            project=settings.ADO_PROJECT,
            api_version=settings.ADO_API_VERSION,
        )


class AzureDevOpsClientError(Exception):
    """Raised when an Azure DevOps request fails."""

    def __init__(self, status_code: int, path: str, summary: str) -> None:
        self.status_code = status_code
        self.path = path
        self.summary = summary
        super().__init__(
            f"Azure DevOps request failed status_code={status_code} path={path} summary={summary}"
        )


class AzureDevOpsBaseClient:
    """Reusable async Azure DevOps REST client."""

    def __init__(
        self,
        config: AzureDevOpsClientConfig,
        token_provider: AdoTokenProvider,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._token_provider = token_provider
        self._http_client = http_client or httpx.AsyncClient(timeout=config.timeout_seconds)
        self._owns_http_client = http_client is None

    def _build_url(self, path: str) -> str:
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self._config.base_url}{normalized_path}"

    def _prepare_params(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resolved_params = dict(params or {})
        resolved_params.setdefault("api-version", self._config.api_version)
        return resolved_params

    @staticmethod
    def _safe_response_summary(response: httpx.Response) -> str:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                payload = response.json()
            except ValueError:
                pass
            else:
                if isinstance(payload, dict):
                    for key in ("message", "error", "typeKey"):
                        value = payload.get(key)
                        if value is not None:
                            return str(value)[:300]
                return str(payload)[:300]
        return response.text[:300]

    async def _request_json(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self._build_url(path)
        query_params = self._prepare_params(params)
        headers = await self._token_provider.get_auth_headers()

        for attempt in range(self._config.max_retries + 1):
            started_at = time.perf_counter()
            try:
                response = await self._http_client.request(
                    method=method,
                    url=url,
                    params=query_params,
                    headers=headers,
                    json=body,
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "ado_request_error method=%s path=%s attempt=%s error=%s",
                    method,
                    path,
                    attempt + 1,
                    exc.__class__.__name__,
                )
                if attempt >= self._config.max_retries:
                    raise AzureDevOpsClientError(
                        status_code=0,
                        path=path,
                        summary=f"request_error: {exc.__class__.__name__}",
                    ) from exc
                await asyncio.sleep(self._config.retry_backoff_seconds * (2**attempt))
                continue

            duration_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "ado_request method=%s path=%s status=%s duration_ms=%s attempt=%s",
                method,
                path,
                response.status_code,
                duration_ms,
                attempt + 1,
            )

            should_retry_response = (
                response.status_code in _TRANSIENT_STATUS_CODES
                and attempt < self._config.max_retries
            )
            if should_retry_response:
                await asyncio.sleep(self._config.retry_backoff_seconds * (2**attempt))
                continue

            if not response.is_success:
                raise AzureDevOpsClientError(
                    status_code=response.status_code,
                    path=path,
                    summary=self._safe_response_summary(response),
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise AzureDevOpsClientError(
                    status_code=response.status_code,
                    path=path,
                    summary="invalid_json_response",
                ) from exc

            if not isinstance(payload, dict):
                raise AzureDevOpsClientError(
                    status_code=response.status_code,
                    path=path,
                    summary="expected_json_object",
                )

            return payload

        raise AzureDevOpsClientError(status_code=0, path=path, summary="retry_exhausted")

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute an authenticated GET request and return a JSON object."""

        return await self._request_json(method="GET", path=path, params=params)

    async def _post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated POST request and return a JSON object."""

        return await self._request_json(method="POST", path=path, params=params, body=body)

    async def aclose(self) -> None:
        """Close owned HTTP client resources."""

        if self._owns_http_client:
            await self._http_client.aclose()

