"""Small cache-backed rate limiting helpers for public-facing endpoints."""

from __future__ import annotations

import time
from hashlib import sha256

from django.core.cache import cache


def _client_ip(request) -> str:
    """Return the best-effort client IP for low-risk rate limiting."""
    forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded_for or request.META.get("REMOTE_ADDR", "").strip() or "unknown"


def _rate_limit_key(request, scope: str, extra_identifier: str = "") -> str:
    """Build a stable cache key for a scope and caller fingerprint."""
    fingerprint = f"{scope}:{_client_ip(request)}:{extra_identifier.strip().lower()}"
    digest = sha256(fingerprint.encode("utf-8")).hexdigest()
    return f"rate-limit:{scope}:{digest}"


def is_rate_limited(
    request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    extra_identifier: str = "",
) -> bool:
    """Record an attempt and return whether the caller has exceeded the limit."""
    if limit <= 0 or window_seconds <= 0:
        return False

    now = time.time()
    key = _rate_limit_key(request, scope, extra_identifier=extra_identifier)
    attempts = [value for value in cache.get(key, []) if value > now - window_seconds]
    if len(attempts) >= limit:
        cache.set(key, attempts, timeout=window_seconds)
        return True

    attempts.append(now)
    cache.set(key, attempts, timeout=window_seconds)
    return False
