"""Content Security Policy response middleware."""

from urllib.parse import urlparse

from django.conf import settings

SELF_SOURCE = "'self'"
NONE_SOURCE = "'none'"
UNSAFE_INLINE_SOURCE = "'unsafe-inline'"
UNSAFE_EVAL_SOURCE = "'unsafe-eval'"
DATA_SOURCE = "data:"
BLOB_SOURCE = "blob:"
HTTPS_SOURCE = "https:"

KIT_ORIGIN = "https://josephlovesjohn.kit.com"
KIT_RUNTIME_ORIGIN = "https://f.convertkit.com"
KIT_FORM_ORIGIN = "https://app.kit.com"
STRIPE_ORIGIN = "https://checkout.stripe.com"
RECAPTCHA_ORIGIN = "https://www.google.com"
RECAPTCHA_STATIC_ORIGIN = "https://www.gstatic.com"
SOUNDCLOUD_WIDGET_ORIGIN = "https://w.soundcloud.com"
GOOGLE_FONTS_STYLES_ORIGIN = "https://fonts.googleapis.com"
GOOGLE_FONTS_FILES_ORIGIN = "https://fonts.gstatic.com"
META_PIXEL_SCRIPT_ORIGIN = "https://connect.facebook.net"
META_PIXEL_EVENT_ORIGIN = "https://www.facebook.com"


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
    extra_sources = list(getattr(settings, "CONTENT_SECURITY_POLICY_EXTRA_SOURCES", []))

    directives = [
        _directive("default-src", [SELF_SOURCE]),
        _directive("base-uri", [SELF_SOURCE]),
        _directive("object-src", [NONE_SOURCE]),
        _directive("frame-ancestors", [NONE_SOURCE]),
        _directive("form-action", [SELF_SOURCE, KIT_ORIGIN, KIT_FORM_ORIGIN, STRIPE_ORIGIN]),
        _directive(
            "script-src",
            [
                SELF_SOURCE,
                UNSAFE_INLINE_SOURCE,
                UNSAFE_EVAL_SOURCE,
                plausible_origin,
                KIT_ORIGIN,
                KIT_RUNTIME_ORIGIN,
                RECAPTCHA_ORIGIN,
                RECAPTCHA_STATIC_ORIGIN,
                META_PIXEL_SCRIPT_ORIGIN,
                *extra_sources,
            ],
        ),
        _directive("style-src", [SELF_SOURCE, UNSAFE_INLINE_SOURCE, GOOGLE_FONTS_STYLES_ORIGIN]),
        _directive(
            "img-src",
            [
                SELF_SOURCE,
                DATA_SOURCE,
                BLOB_SOURCE,
                HTTPS_SOURCE,
                public_asset_origin,
                media_files_origin,
                *extra_sources,
            ],
        ),
        _directive(
            "media-src",
            [
                SELF_SOURCE,
                BLOB_SOURCE,
                HTTPS_SOURCE,
                public_asset_origin,
                media_files_origin,
                *extra_sources,
            ],
        ),
        _directive("font-src", [SELF_SOURCE, DATA_SOURCE, GOOGLE_FONTS_FILES_ORIGIN]),
        _directive(
            "connect-src",
            [
                SELF_SOURCE,
                plausible_origin,
                KIT_ORIGIN,
                KIT_RUNTIME_ORIGIN,
                KIT_FORM_ORIGIN,
                RECAPTCHA_ORIGIN,
                META_PIXEL_EVENT_ORIGIN,
                *extra_sources,
            ],
        ),
        _directive("frame-src", [KIT_ORIGIN, STRIPE_ORIGIN, RECAPTCHA_ORIGIN, SOUNDCLOUD_WIDGET_ORIGIN]),
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
