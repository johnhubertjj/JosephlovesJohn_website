"""Tests for the Content Security Policy middleware."""

import pytest
from django.urls import reverse
from josephlovesjohn_site.csp import build_content_security_policy

pytestmark = [pytest.mark.django_db, pytest.mark.smoke]


def test_content_security_policy_header_is_sent(client) -> None:
    """Every normal page response should include the CSP header."""
    response = client.get(reverse("main_site:main"))

    policy = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in policy
    assert "object-src 'none'" in policy
    assert "frame-ancestors 'none'" in policy
    assert (
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io "
        "https://josephlovesjohn.kit.com https://f.convertkit.com"
    ) in policy
    assert (
        "form-action 'self' https://josephlovesjohn.kit.com "
        "https://app.kit.com https://checkout.stripe.com"
    ) in policy
    assert "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com" in policy
    assert "font-src 'self' data: https://fonts.gstatic.com" in policy


def test_content_security_policy_can_run_in_report_only_mode(client, settings) -> None:
    """Report-only mode should use the matching report-only header name."""
    settings.CONTENT_SECURITY_POLICY_REPORT_ONLY = True

    response = client.get(reverse("main_site:main"))

    assert "Content-Security-Policy-Report-Only" in response.headers
    assert "Content-Security-Policy" not in response.headers


def test_content_security_policy_includes_configured_asset_origins(settings) -> None:
    """Configured public asset origins should be allowed for media and images."""
    settings.PUBLIC_ASSET_BASE_URL = "https://pub.example.com/assets"
    settings.MEDIA_FILES_BASE_URL = "https://media.example.com/uploads"
    settings.CONTENT_SECURITY_POLICY_EXTRA_SOURCES = ["https://extra.example.com"]

    policy = build_content_security_policy()

    assert "https://pub.example.com" in policy
    assert "https://media.example.com" in policy
    assert "https://extra.example.com" in policy


def test_content_security_policy_upgrade_insecure_requests_is_configurable(settings) -> None:
    """The HTTPS upgrade directive should be optional for HTTP-only browser test servers."""
    settings.CONTENT_SECURITY_POLICY_UPGRADE_INSECURE_REQUESTS = True
    assert "upgrade-insecure-requests" in build_content_security_policy()

    settings.CONTENT_SECURITY_POLICY_UPGRADE_INSECURE_REQUESTS = False
    assert "upgrade-insecure-requests" not in build_content_security_policy()
