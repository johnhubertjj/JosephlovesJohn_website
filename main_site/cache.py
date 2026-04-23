"""Cache helpers for shared main-site content."""

from __future__ import annotations

from collections.abc import Callable, Collection
from contextvars import ContextVar
from typing import TypeVar

from django.conf import settings
from django.core.cache import cache

T = TypeVar("T")

_VERSION_KEY = "main-site:content-version"
_MISSING = object()
_REQUEST_CACHE_VERSION: ContextVar[int | None] = ContextVar("main_site_request_cache_version", default=None)


def _content_cache_ttl() -> int:
    """Return the configured cache TTL for shared site data."""
    return max(getattr(settings, "SITE_CONTENT_CACHE_TTL", 0), 0)


def _load_content_cache_version() -> int:
    """Return the current cache version from the backing cache."""
    version = cache.get(_VERSION_KEY)
    if isinstance(version, int) and version > 0:
        return version

    cache.set(_VERSION_KEY, 1, timeout=None)
    return 1


def _content_cache_version() -> int:
    """Return the current cache version for shared content."""
    request_version = _REQUEST_CACHE_VERSION.get()
    if isinstance(request_version, int) and request_version > 0:
        return request_version
    return _load_content_cache_version()


def _content_cache_key(name: str) -> str:
    """Build a versioned cache key for a shared-content payload."""
    return f"main-site:{name}:v{_content_cache_version()}"


def _should_cache_value(value: object, *, cache_empty: bool) -> bool:
    """Return whether a shared-content value should be stored in cache."""
    if cache_empty:
        return True

    if value is None:
        return False

    if isinstance(value, (str, bytes, bytearray)):
        return len(value) > 0

    if isinstance(value, Collection):
        return len(value) > 0

    return True


def cache_shared_content(name: str, builder: Callable[[], T], *, cache_empty: bool = True) -> T:
    """Return a shared-content payload, using cache when enabled."""
    ttl = _content_cache_ttl()
    if ttl <= 0:
        return builder()

    key = _content_cache_key(name)
    cached = cache.get(key, _MISSING)
    if cached is not _MISSING:
        if _should_cache_value(cached, cache_empty=cache_empty):
            return cached
        cache.delete(key)

    value = builder()
    if _should_cache_value(value, cache_empty=cache_empty):
        cache.set(key, value, timeout=ttl)
    return value


def invalidate_shared_content_cache() -> None:
    """Bump the cache version so future reads rebuild shared content."""
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        cache.set(_VERSION_KEY, 2, timeout=None)


class SharedContentCacheContextMiddleware:
    """Reuse one shared-content cache version lookup for the current request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _content_cache_ttl() <= 0:
            return self.get_response(request)

        token = _REQUEST_CACHE_VERSION.set(_load_content_cache_version())
        try:
            return self.get_response(request)
        finally:
            _REQUEST_CACHE_VERSION.reset(token)
