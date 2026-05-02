"""Validate Phase-0 environment configuration safely."""

from __future__ import annotations

from app.core.config import get_settings


def _is_present(value: str | None) -> bool:
    return bool(value and value.strip())


def main() -> int:
    """Load settings and print presence/absence of key configuration values."""

    settings = get_settings()

    required_now: dict[str, str | None] = {
        "APP_ENV": settings.APP_ENV,
        "APP_HOST": settings.APP_HOST,
        "APP_PORT": str(settings.APP_PORT),
        "LOG_LEVEL": settings.LOG_LEVEL,
        "DATA_DIR": str(settings.DATA_DIR),
        "ADO_ORGANIZATION": settings.ADO_ORGANIZATION,
        "ADO_PROJECT": settings.ADO_PROJECT,
        "ADO_API_VERSION": settings.ADO_API_VERSION,
    }
    required_later: dict[str, str | None] = {
        "AZURE_TENANT_ID": settings.AZURE_TENANT_ID,
        "AZURE_CLIENT_ID": settings.AZURE_CLIENT_ID,
        "AZURE_CLIENT_SECRET": settings.AZURE_CLIENT_SECRET,
        "AZURE_OPENAI_ENDPOINT": settings.AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_API_VERSION": settings.AZURE_OPENAI_API_VERSION,
        "AZURE_OPENAI_DEPLOYMENT": settings.AZURE_OPENAI_DEPLOYMENT,
    }

    print("Configuration presence summary")
    print("phase1_required_for_app_and_smoke:")
    for key, value in required_now.items():
        print(f"  - {key}: {'present' if _is_present(value) else 'missing'}")

    print("future_phase_values:")
    for key, value in required_later.items():
        print(f"  - {key}: {'present' if _is_present(value) else 'missing'}")

    print("Note: secret values are intentionally never printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
