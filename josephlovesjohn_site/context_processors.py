"""Template context shared across the JosephlovesJohn project."""

from django.conf import settings

from .recaptcha import recaptcha_is_enabled


def recaptcha(request):
    """Expose the minimal reCAPTCHA settings needed by protected forms."""

    return {
        "recaptcha": {
            "enabled": recaptcha_is_enabled(),
            "site_key": settings.RECAPTCHA_SITE_KEY,
        }
    }
