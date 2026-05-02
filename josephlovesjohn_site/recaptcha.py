"""Helpers for verifying Google reCAPTCHA v3 tokens."""

from __future__ import annotations

import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

logger = logging.getLogger(__name__)


def _score_from_result(result: dict) -> float:
    """Return a numeric score from a siteverify response."""

    try:
        return float(result.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def recaptcha_is_enabled() -> bool:
    """Return whether reCAPTCHA verification should run for protected forms."""

    return bool(settings.RECAPTCHA_SITE_KEY and settings.RECAPTCHA_SECRET_KEY)


def verify_recaptcha_request(request, *, expected_action: str) -> bool:
    """Verify the submitted reCAPTCHA v3 token against Google's siteverify API."""

    if not recaptcha_is_enabled():
        return True

    token = (request.POST.get("g-recaptcha-response") or "").strip()
    if not token:
        return False

    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": token,
    }
    remote_ip = request.META.get("REMOTE_ADDR")
    if remote_ip:
        payload["remoteip"] = remote_ip

    encoded_payload = urlencode(payload).encode("utf-8")
    verify_request = Request(
        settings.RECAPTCHA_VERIFY_URL,
        data=encoded_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urlopen(verify_request, timeout=settings.RECAPTCHA_VERIFY_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("reCAPTCHA verification failed unexpectedly: %s", exc)
        return False

    if not result.get("success"):
        return False
    if result.get("action") != expected_action:
        return False
    if _score_from_result(result) < settings.RECAPTCHA_MIN_SCORE:
        return False

    allowed_hostnames = set(settings.RECAPTCHA_ALLOWED_HOSTNAMES)
    if allowed_hostnames and result.get("hostname") not in allowed_hostnames:
        return False

    return True
