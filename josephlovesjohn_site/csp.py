"""Content Security Policy response middleware."""

from urllib.parse import urlparse

from django.conf import settings


def _origin(value: str) -> str:
    """Return the scheme and host for an absolute URL."""
    parsed = urlparse((value or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def _unique_sources(sources: list[str]) -> list[str]:
    """Deduplicate CSP sources while preserving order."""
    seen = set()
    unique = []
    for source in sources:
        cleaned = source.strip()
        if cleaned and cleaned not in seen:
            unique.append(cleaned)
            seen.add(cleaned)
    return unique


def _directive(name: str, sources: list[str]) -> str:
    """Build one CSP directive from a list of allowed sources."""
    return f"{name} {' '.join(_unique_sources(sources))}"


def build_content_security_policy() -> str:
    """Build the response Content-Security-Policy header value."""
    plausible_origin = _origin(getattr(settings, "PLAUSIBLE_SCRIPT_SRC", ""))
    public_asset_origin = _origin(getattr(settings, "PUBLIC_ASSET_BASE_URL", ""))
    media_files_origin = _origin(getattr(settings, "MEDIA_FILES_BASE_URL", ""))
    kit_origin = "https://josephlovesjohn.kit.com"
    kit_runtime_origin = "https://f.convertkit.com"
    kit_form_origin = "https://app.kit.com"
    stripe_origin = "https://checkout.stripe.com"
    recaptcha_origin = "https://www.google.com"
    recaptcha_static_origin = "https://www.gstatic.com"
    google_fonts_styles_origin = "https://fonts.googleapis.com"
    google_fonts_files_origin = "https://fonts.gstatic.com"
    meta_pixel_script_origin = "https://connect.facebook.net"
    meta_pixel_event_origin = "https://www.facebook.com"
    extra_sources = list(getattr(settings, "CONTENT_SECURITY_POLICY_EXTRA_SOURCES", []))

    directives = [
        _directive("default-src", ["'self'"]),
        _directive("base-uri", ["'self'"]),
        _directive("object-src", ["'none'"]),
        _directive("frame-ancestors", ["'none'"]),
        _directive("form-action", ["'self'", kit_origin, kit_form_origin, stripe_origin]),
        _directive(
            "script-src",
            [
                "'self'",
                "'unsafe-inline'",
                "'unsafe-eval'",
                plausible_origin,
                kit_origin,
                kit_runtime_origin,
                recaptcha_origin,
                recaptcha_static_origin,
                meta_pixel_script_origin,
                *extra_sources,
            ],
        ),
        _directive("style-src", ["'self'", "'unsafe-inline'", google_fonts_styles_origin]),
        _directive(
            "img-src",
            [
                "'self'",
                "data:",
                "blob:",
                "https:",
                public_asset_origin,
                media_files_origin,
                *extra_sources,
            ],
        ),
        _directive(
            "media-src",
            [
                "'self'",
                "blob:",
                "https:",
                public_asset_origin,
                media_files_origin,
                *extra_sources,
            ],
        ),
        _directive("font-src", ["'self'", "data:", google_fonts_files_origin]),
        _directive(
            "connect-src",
            [
                "'self'",
                plausible_origin,
                kit_origin,
                kit_runtime_origin,
                kit_form_origin,
                recaptcha_origin,
                meta_pixel_event_origin,
                *extra_sources,
            ],
        ),
        _directive("frame-src", [kit_origin, stripe_origin, recaptcha_origin]),
    ]

    if settings.CONTENT_SECURITY_POLICY_UPGRADE_INSECURE_REQUESTS:
        directives.append("upgrade-insecure-requests")

    return "; ".join(directives)


class ContentSecurityPolicyMiddleware:
    """Attach a conservative Content Security Policy to every response."""

    def __init__(self, get_response):
        """Store the wrapped response callable."""
        self.get_response = get_response

    def __call__(self, request):
        """Attach CSP unless the view already set one explicitly."""
        response = self.get_response(request)
        header_name = (
            "Content-Security-Policy-Report-Only"
            if settings.CONTENT_SECURITY_POLICY_REPORT_ONLY
            else "Content-Security-Policy"
        )
        response.setdefault(header_name, build_content_security_policy())
        return response
