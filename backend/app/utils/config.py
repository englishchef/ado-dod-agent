"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from backend.app.core.enterprise_config import resolve_runtime_config


class Settings(BaseSettings):
    """Application settings loaded from `.env` and process environment."""

    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    AZURE_TENANT_ID: str | None = None
    AZURE_CLIENT_ID: str | None = None
    AZURE_CLIENT_SECRET: str | None = None
    AZURE_CREDENTIAL_MODE: str = "default"
    AZURE_USER_ASSIGNED_CLIENT_ID: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_VERSION: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    AZURE_OPENAI_AUTH_MODE: str = "entra"

    LLM_TEMPERATURE: float = 0
    LLM_MAX_TOKENS: int = 1000
    LLM_TIMEOUT_SECONDS: int = 60

    ADO_ORGANIZATION: str | None = None
    ADO_PROJECT: str | None = None
    ADO_API_VERSION: str = "7.1"
    ADO_AUTH_MODE: str | None = None

    DATA_DIR: Path = Path("data")
    DOD_STORAGE_BACKEND: str = "local_json"
    COSMOS_AUTH_MODE: str | None = None
    COSMOS_ENDPOINT: str | None = None
    COSMOS_KEY: str | None = None
    COSMOS_DATABASE: str | None = None
    COSMOS_CONTAINER: str | None = None
    COSMOS_DISABLE_TLS_VERIFY: bool = False

    # Deprecated Phase 10C-local aliases. Kept only to avoid breaking local .env.local files.
    DOD_COSMOS_EMULATOR_ENABLED: bool = False
    COSMOS_LOCAL_ENDPOINT: str | None = None
    COSMOS_LOCAL_DATABASE: str | None = None
    COSMOS_LOCAL_CONTAINER: str | None = None
    COSMOS_LOCAL_AUTH_MODE: str | None = None
    COSMOS_LOCAL_KEY: str | None = None
    COSMOS_LOCAL_DISABLE_TLS_VERIFY: bool = False
    DOD_GRAPH_NAME: str = "dod"
    DOD_ASSISTANT_NAME: str = "dod"
    AGENT_CONFIG_KEY_VAULT_URL: str | None = None
    AGENT_CONFIG_SECRET_NAME: str | None = None
    LANGSMITH_TRACING: bool | None = None
    TRACING_ENABLED: bool | None = None
    LANGSMITH_PROJECT: str = "dod-agent-local"
    LANGSMITH_ENDPOINT: str | None = None
    LANGSMITH_TLS_VERIFY: bool | None = None
    LANGSMITH_CA_BUNDLE: str | None = None
    LANGGRAPH_API_URL: str | None = None
    LANGGRAPH_ASSISTANT_ID: str | None = None
    LANGGRAPH_API_KEY_HEADER: str | None = None
    LANGGRAPH_KEY_VAULT_URL: str | None = None
    LANGGRAPH_KEY_VAULT_SECRET_NAME: str | None = None
    DOD_TRACE_MODE: str = "summary"
    DOD_GRAPH_STATE_WARN_BYTES: int = 262_144
    DOD_GRAPH_STATE_MAX_BYTES: int = 1_048_576
    DOD_CONFIDENCE_THRESHOLD: float = 0.70
    DOD_HIGH_RISK_CONFIDENCE_THRESHOLD: float = 0.85
    DOD_SHORT_DESCRIPTION_MAX_LENGTH: int = 160

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource | Any, ...]:
        """Place Key Vault JSON config after process env and before `.env`."""

        return (
            init_settings,
            env_settings,
            _enterprise_runtime_config_source,
            dotenv_settings,
            file_secret_settings,
        )

    def model_post_init(self, __context: Any) -> None:
        """Normalize backward-compatible enterprise aliases."""

        if self.LANGSMITH_TRACING is None and self.TRACING_ENABLED is not None:
            self.LANGSMITH_TRACING = self.TRACING_ENABLED

    @property
    def data_subdirectories(self) -> tuple[Path, Path, Path, Path]:
        """Return all data directories used by the pipeline lifecycle."""

        root = self.DATA_DIR
        return (root / "raw", root / "normalized", root / "evidence", root / "output")

    @property
    def resolved_cosmos_auth_mode(self) -> str:
        """Return official Cosmos auth mode, honoring deprecated local aliases."""

        return self.COSMOS_AUTH_MODE or self.COSMOS_LOCAL_AUTH_MODE or "emulator_key"

    @property
    def resolved_cosmos_endpoint(self) -> str | None:
        """Return official Cosmos endpoint, honoring deprecated local aliases."""

        return self.COSMOS_ENDPOINT or self.COSMOS_LOCAL_ENDPOINT

    @property
    def resolved_cosmos_key(self) -> str | None:
        """Return official Cosmos key, honoring deprecated local aliases."""

        return self.COSMOS_KEY or self.COSMOS_LOCAL_KEY

    @property
    def resolved_cosmos_database(self) -> str | None:
        """Return official Cosmos database, honoring deprecated local aliases."""

        return self.COSMOS_DATABASE or self.COSMOS_LOCAL_DATABASE

    @property
    def resolved_cosmos_container(self) -> str | None:
        """Return official Cosmos container, honoring deprecated local aliases."""

        return self.COSMOS_CONTAINER or self.COSMOS_LOCAL_CONTAINER

    @property
    def resolved_cosmos_disable_tls_verify(self) -> bool:
        """Return whether Cosmos TLS verification is disabled."""

        return self.COSMOS_DISABLE_TLS_VERIFY or self.COSMOS_LOCAL_DISABLE_TLS_VERIFY

    @property
    def resolved_langgraph_assistant_id(self) -> str:
        """Return the LangGraph platform assistant id, defaulting to dod."""

        return self.LANGGRAPH_ASSISTANT_ID or self.DOD_ASSISTANT_NAME or "dod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


def ensure_data_directories(settings: Settings) -> None:
    """Create local data directories required by the service."""

    for directory in settings.data_subdirectories:
        directory.mkdir(parents=True, exist_ok=True)


def _enterprise_runtime_config_source() -> dict[str, Any]:
    return resolve_runtime_config(strict=False)
