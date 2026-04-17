"""Helpers for building canonical public URLs for the site."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from django.conf import settings


def site_base_url(request=None) -> str:
    """Return the canonical public site base URL when available."""
    configured = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    if request is not None:
        return request.build_absolute_uri("/").rstrip("/")
    return ""


def absolute_site_url(path: str, request=None) -> str:
    """Build an absolute public URL for a local path or return an existing external URL."""
    cleaned = (path or "").strip()
    if not cleaned:
        return site_base_url(request)
    if cleaned.startswith(("http://", "https://", "//")):
        return cleaned

    base_url = site_base_url(request)
    if not base_url:
        return cleaned
    return urljoin(f"{base_url}/", cleaned.lstrip("/"))


def site_context(request=None) -> dict[str, str]:
    """Return the canonical site context used by customer-facing emails."""
    base_url = site_base_url(request) or "http://127.0.0.1:8000"
    parsed = urlsplit(base_url)
    domain = parsed.netloc or "127.0.0.1:8000"
    protocol = parsed.scheme or "http"
    return {
        "domain": domain,
        "site_name": domain,
        "protocol": protocol,
    }
