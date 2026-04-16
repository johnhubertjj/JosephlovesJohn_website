"""Template context processors for the main site."""

from django.conf import settings


def analytics(request):
    """Expose analytics configuration to Django templates."""

    del request
    plausible_domain = settings.PLAUSIBLE_DOMAIN.strip()
    return {
        "analytics": {
            "plausible_enabled": bool(plausible_domain),
            "plausible_domain": plausible_domain,
            "plausible_script_src": settings.PLAUSIBLE_SCRIPT_SRC.strip(),
        }
    }
