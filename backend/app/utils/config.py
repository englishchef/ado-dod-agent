"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from `.env` and process environment."""

    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    AZURE_TENANT_ID: str | None = None
    AZURE_CLIENT_ID: str | None = None
    AZURE_CLIENT_SECRET: str | None = None
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

    DATA_DIR: Path = Path("data")
    DOD_CONFIDENCE_THRESHOLD: float = 0.70
    DOD_HIGH_RISK_CONFIDENCE_THRESHOLD: float = 0.85

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def data_subdirectories(self) -> tuple[Path, Path, Path, Path]:
        """Return all data directories used by the pipeline lifecycle."""

        root = self.DATA_DIR
        return (root / "raw", root / "normalized", root / "evidence", root / "output")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()


def ensure_data_directories(settings: Settings) -> None:
    """Create local data directories required by the service."""

    for directory in settings.data_subdirectories:
        directory.mkdir(parents=True, exist_ok=True)
