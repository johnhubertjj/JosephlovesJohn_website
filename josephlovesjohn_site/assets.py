"""Helpers for resolving site assets from static files or a public CDN."""

from collections.abc import Callable

from django.conf import settings
from django.templatetags.static import static as static_url


def is_external_url(value):
    """Return whether the supplied asset value is already an absolute URL."""
    cleaned = (value or "").strip()
    return cleaned.startswith(("http://", "https://", "//"))


def normalize_asset_path(value):
    """Normalize a relative asset path for static/CDN lookup."""
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    if is_external_url(cleaned):
        return cleaned
    cleaned = cleaned.lstrip("/")
    if cleaned.startswith("static/"):
        cleaned = cleaned[7:]
    return cleaned


def public_asset_url(value):
    """Return a public URL for a stored asset path or absolute URL."""
    normalized = normalize_asset_path(value)
    if not normalized:
        return ""
    if is_external_url(normalized):
        return normalized

    asset_base_url = getattr(settings, "PUBLIC_ASSET_BASE_URL", "").strip().rstrip("/")
    if asset_base_url:
        return f"{asset_base_url}/{normalized}"

    try:
        return static_url(normalized)
    except ValueError:
        return f"{settings.STATIC_URL}{normalized.lstrip('/')}"


def resolve_public_asset_source(value, *, file_exists: Callable[[str], bool] | None = None):
    """Resolve an asset path to a normalized public source payload.

    The optional ``file_exists`` callback is used to confirm repo-backed static
    files when no public asset base URL is configured.
    """

    normalized = normalize_asset_path(value)
    if not normalized:
        return None

    if is_external_url(normalized):
        return {
            "path": normalized,
            "url": normalized,
            "is_static": False,
        }

    file_is_available = True if getattr(settings, "PUBLIC_ASSET_BASE_URL", "").strip() else bool(
        file_exists and file_exists(normalized)
    )
    if not file_is_available:
        return None

    return {
        "path": normalized,
        "url": public_asset_url(normalized),
        "is_static": True,
    }
