"""Template context processors for the main site."""

from django.conf import settings


def analytics(request):
    """Expose analytics configuration to Django templates."""

    plausible_domain = settings.PLAUSIBLE_DOMAIN.strip()
    meta_pixel_id = settings.META_PIXEL_ID.strip()
    optional_cookies_allowed = request.COOKIES.get("site_cookie_preference") == "all"
    return {
        "analytics": {
            "plausible_enabled": bool(plausible_domain),
            "plausible_domain": plausible_domain,
            "plausible_script_src": settings.PLAUSIBLE_SCRIPT_SRC.strip(),
            "meta_pixel_enabled": bool(meta_pixel_id),
            "meta_pixel_id": meta_pixel_id,
            "meta_pixel_noscript_enabled": bool(meta_pixel_id) and optional_cookies_allowed,
        }
    }
