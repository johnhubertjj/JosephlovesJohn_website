"""Tests for Google reCAPTCHA v3 verification helpers."""

import json

import pytest
from django.test import RequestFactory, override_settings
from josephlovesjohn_site import recaptcha

pytestmark = pytest.mark.smoke


class FakeRecaptchaResponse:
    """Small context-manager response double for urllib."""

    def __init__(self, payload):
        """Store the JSON payload returned by the fake siteverify API."""
        self.payload = payload

    def __enter__(self):
        """Return the fake response object."""
        return self

    def __exit__(self, exc_type, exc, traceback):
        """Allow the response context to close cleanly."""
        return False

    def read(self):
        """Return encoded JSON response bytes."""
        return json.dumps(self.payload).encode("utf-8")


def test_recaptcha_verification_is_disabled_without_keys(rf: RequestFactory) -> None:
    """Missing keys should keep local development and tests friction-free."""
    request = rf.post("/contact/", {})

    assert recaptcha.verify_recaptcha_request(request, expected_action="contact") is True


@override_settings(
    RECAPTCHA_SITE_KEY="site-key",
    RECAPTCHA_SECRET_KEY="secret-key",
    RECAPTCHA_MIN_SCORE=0.5,
    RECAPTCHA_ALLOWED_HOSTNAMES=["josephlovesjohn.com"],
)
def test_recaptcha_verifies_expected_action_score_and_hostname(monkeypatch, rf: RequestFactory) -> None:
    """A valid token should pass when action, score, and hostname match."""
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeRecaptchaResponse(
            {
                "success": True,
                "score": 0.9,
                "action": "login",
                "hostname": "josephlovesjohn.com",
            }
        )

    monkeypatch.setattr(recaptcha, "urlopen", fake_urlopen)
    request = rf.post("/shop/login/", {"g-recaptcha-response": "token"}, REMOTE_ADDR="203.0.113.10")

    assert recaptcha.verify_recaptcha_request(request, expected_action="login") is True
    assert calls[0][1] == 3
    assert calls[0][0].full_url == "https://www.google.com/recaptcha/api/siteverify"


@override_settings(
    RECAPTCHA_SITE_KEY="site-key",
    RECAPTCHA_SECRET_KEY="secret-key",
    RECAPTCHA_MIN_SCORE=0.5,
    RECAPTCHA_ALLOWED_HOSTNAMES=["josephlovesjohn.com"],
)
@pytest.mark.parametrize(
    "payload",
    (
        {"success": False, "score": 0.9, "action": "login", "hostname": "josephlovesjohn.com"},
        {"success": True, "score": 0.4, "action": "login", "hostname": "josephlovesjohn.com"},
        {"success": True, "score": 0.9, "action": "register", "hostname": "josephlovesjohn.com"},
        {"success": True, "score": 0.9, "action": "login", "hostname": "spam.example"},
    ),
)
def test_recaptcha_rejects_failed_low_score_wrong_action_or_wrong_hostname(
    monkeypatch,
    rf: RequestFactory,
    payload,
) -> None:
    """Invalid siteverify responses should fail closed."""
    monkeypatch.setattr(recaptcha, "urlopen", lambda request, timeout: FakeRecaptchaResponse(payload))
    request = rf.post("/shop/login/", {"g-recaptcha-response": "token"})

    assert recaptcha.verify_recaptcha_request(request, expected_action="login") is False
