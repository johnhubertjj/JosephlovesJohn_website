"""Cache helpers for shared main-site content."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from django.conf import settings
from django.core.cache import cache

T = TypeVar("T")

_VERSION_KEY = "main-site:content-version"
_MISSING = object()


def _content_cache_ttl() -> int:
    """Return the configured cache TTL for shared site data."""
    return max(getattr(settings, "SITE_CONTENT_CACHE_TTL", 0), 0)


def _content_cache_version() -> int:
    """Return the current cache version for shared content."""
    version = cache.get(_VERSION_KEY)
    if isinstance(version, int) and version > 0:
        return version

    cache.set(_VERSION_KEY, 1, timeout=None)
    return 1


def _content_cache_key(name: str) -> str:
    """Build a versioned cache key for a shared-content payload."""
    return f"main-site:{name}:v{_content_cache_version()}"


def cache_shared_content(name: str, builder: Callable[[], T]) -> T:
    """Return a shared-content payload, using cache when enabled."""
    ttl = _content_cache_ttl()
    if ttl <= 0:
        return builder()

    key = _content_cache_key(name)
    cached = cache.get(key, _MISSING)
    if cached is not _MISSING:
        return cached

    value = builder()
    cache.set(key, value, timeout=ttl)
    return value


def invalidate_shared_content_cache() -> None:
    """Bump the cache version so future reads rebuild shared content."""
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        cache.set(_VERSION_KEY, 2, timeout=None)
