"""Helpers for verifying Google reCAPTCHA v3 tokens."""

from __future__ import annotations

import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.http.request import split_domain_port

logger = logging.getLogger(__name__)


def _score_from_result(result: dict) -> float:
    """Return a numeric score from a siteverify response."""

    try:
        return float(result.get("score", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _normalise_hostname(hostname: str | None) -> str:
    """Return a lower-case hostname without a port or trailing dot."""

    return (hostname or "").strip().lower().rstrip(".")


def _request_hostname(request) -> str:
    """Extract the current request hostname for reCAPTCHA domain checks."""

    domain, _port = split_domain_port(request.get_host())
    return _normalise_hostname(domain)


def recaptcha_hostname_is_allowed(hostname: str | None) -> bool:
    """Return whether a hostname is allowed to run reCAPTCHA."""

    allowed_hostnames = {_normalise_hostname(host) for host in settings.RECAPTCHA_ALLOWED_HOSTNAMES}
    allowed_hostnames.discard("")
    if not allowed_hostnames:
        return True

    return _normalise_hostname(hostname) in allowed_hostnames


def recaptcha_is_enabled(request=None) -> bool:
    """Return whether reCAPTCHA verification should run for protected forms."""

    if not settings.RECAPTCHA_SITE_KEY or not settings.RECAPTCHA_SECRET_KEY:
        return False
    if request is not None and not recaptcha_hostname_is_allowed(_request_hostname(request)):
        return False

    return True


def verify_recaptcha_request(request, *, expected_action: str) -> bool:
    """Verify the submitted reCAPTCHA v3 token against Google's siteverify API."""

    if not recaptcha_is_enabled(request):
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

    if not recaptcha_hostname_is_allowed(result.get("hostname")):
        return False

    return True
