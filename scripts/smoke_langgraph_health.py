"""Smoke-check the deployed LangGraph platform health endpoint."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.core.langgraph_api_key import (  # noqa: E402
    DEFAULT_LANGGRAPH_API_KEY_HEADER,
    get_langgraph_api_key,
    get_langgraph_api_key_config,
)


def build_health_url(base_url: str) -> str:
    """Return the deployed LangGraph /ok health URL for a base URL."""

    stripped = base_url.strip()
    if not stripped:
        raise ValueError("LANGGRAPH_API_URL or --url is required.")
    parsed = urlsplit(stripped)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("LangGraph URL must include scheme and host.")
    path = parsed.path.rstrip("/")
    if path.endswith("/ok"):
        health_path = path
    else:
        health_path = f"{path}/ok" if path else "/ok"
    return urlunsplit((parsed.scheme, parsed.netloc, health_path, "", ""))


def build_headers(
    *,
    api_key_env: str | None,
    api_key_header: str | None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build optional auth headers without exposing values."""

    if not api_key_env and not api_key_header:
        return {}
    if not api_key_env or not api_key_header:
        raise ValueError("--api-key-env and --api-key-header must be provided together.")
    env = os.environ if environ is None else environ
    value = env.get(api_key_env)
    if not value:
        raise ValueError(f"API key env var {api_key_env} is not set.")
    return {api_key_header: value}


def build_key_vault_headers(
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build auth headers from the LangGraph API-key Key Vault secret."""

    env = os.environ if environ is None else environ
    config = get_langgraph_api_key_config(env)
    api_key = get_langgraph_api_key(strict=True, environ=env)
    if not api_key:
        raise ValueError("LangGraph API key was not resolved.")
    return {config.api_key_header or DEFAULT_LANGGRAPH_API_KEY_HEADER: api_key}


def resolve_tls_verify(raw_value: str, *, environ: Mapping[str, str] | None = None) -> bool | str:
    """Resolve TLS verification setting for httpx."""

    env = os.environ if environ is None else environ
    value = raw_value.strip().lower()
    if value in {"false", "0", "no", "off"}:
        return False
    if value not in {"true", "1", "yes", "on"}:
        raise ValueError("--tls-verify must be true or false.")
    bundle = env.get("LANGGRAPH_CA_BUNDLE") or env.get("LANGSMITH_CA_BUNDLE")
    return bundle if bundle else True


def check_health(
    *,
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
    tls_verify: bool | str,
) -> tuple[int, str]:
    """Call the health endpoint and return status code and safe status text."""

    import httpx

    with httpx.Client(timeout=timeout_seconds, verify=tls_verify) as client:
        response = client.get(url, headers=dict(headers))
    status_text = "ok" if response.status_code == 200 else "unhealthy"
    return response.status_code, status_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate deployed LangGraph /ok health.")
    parser.add_argument("--url", default=None, help="Base LangGraph API URL.")
    parser.add_argument("--api-key-env", default=None, help="Env var holding optional API key.")
    parser.add_argument("--api-key-header", default=None, help="Header name for optional API key.")
    parser.add_argument(
        "--use-api-key",
        "--api-key-required",
        action="store_true",
        dest="use_api_key",
        help="Fetch LangGraph API key from Key Vault and send it as a header.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--tls-verify", choices=("true", "false"), default="true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        base_url = args.url or os.environ.get("LANGGRAPH_API_URL") or ""
        health_url = build_health_url(base_url)
        if args.use_api_key:
            headers = build_key_vault_headers()
        else:
            headers = build_headers(
                api_key_env=args.api_key_env,
                api_key_header=args.api_key_header,
            )
        tls_verify = resolve_tls_verify(args.tls_verify)
        status_code, status_text = check_health(
            url=health_url,
            headers=headers,
            timeout_seconds=args.timeout_seconds,
            tls_verify=tls_verify,
        )
    except Exception as exc:
        print(f"Error: LangGraph health check failed: {type(exc).__name__}: {exc}")
        return 2

    print("LangGraph health smoke")
    print(f"- endpoint: {_safe_url_for_display(health_url)}")
    print(f"- status_code: {status_code}")
    print(f"- status: {status_text}")
    print("- api_key_printed: false")
    return 0 if status_code == 200 else 2


def _safe_url_for_display(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


if __name__ == "__main__":
    raise SystemExit(main())
