"""Helpers for optionally bootstrapping Sentry from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


def _clean_env(value: str | None) -> str | None:
    """Return stripped environment values, normalizing blanks to ``None``."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _env_bool(value: str | None, *, default: bool = False) -> bool:
    """Parse a flexible boolean environment variable value."""
    cleaned = _clean_env(value)
    if cleaned is None:
        return default
    return cleaned.lower() in {"1", "true", "yes", "on"}


def _env_float(value: str | None, *, default: float = 0.0) -> float:
    """Parse a float environment variable, falling back for invalid input."""
    cleaned = _clean_env(value)
    if cleaned is None:
        return default
    try:
        return float(cleaned)
    except ValueError:
        return default


def _load_sentry_sdk() -> tuple[Any, type[Any]]:
    """Import and return the Sentry SDK init callable and Django integration class."""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError as exc:  # pragma: no cover - exercised when the dependency is missing.
        raise RuntimeError(
            "Sentry is configured but sentry-sdk is not installed. Run `uv sync` to install project dependencies."
        ) from exc

    return sentry_sdk.init, DjangoIntegration


def setup_sentry(
    *,
    dsn: str | None,
    environment: str | None = None,
    release: str | None = None,
    traces_sample_rate: float = 0.0,
    send_default_pii: bool = False,
    debug: bool = False,
) -> bool:
    """Initialize Sentry when a DSN is supplied."""
    cleaned_dsn = _clean_env(dsn)
    if not cleaned_dsn:
        return False

    sentry_init, django_integration = _load_sentry_sdk()
    sentry_init(
        dsn=cleaned_dsn,
        environment=environment,
        release=release,
        integrations=[django_integration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=send_default_pii,
        debug=debug,
    )
    return True


def setup_sentry_from_env(environ: Mapping[str, str] | None = None) -> bool:
    """Initialize Sentry from ``SENTRY_*`` environment variables."""
    env = os.environ if environ is None else environ
    return setup_sentry(
        dsn=_clean_env(env.get("SENTRY_DSN")),
        environment=_clean_env(env.get("SENTRY_ENVIRONMENT")),
        release=_clean_env(env.get("SENTRY_RELEASE")),
        traces_sample_rate=_env_float(env.get("SENTRY_TRACES_SAMPLE_RATE"), default=0.0),
        send_default_pii=_env_bool(env.get("SENTRY_SEND_DEFAULT_PII"), default=False),
        debug=_env_bool(env.get("SENTRY_DEBUG"), default=False),
    )
