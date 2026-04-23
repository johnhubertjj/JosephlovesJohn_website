"""Template helpers for resolving static/CDN asset URLs."""

from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from josephlovesjohn_site.assets import public_asset_url

register = template.Library()


@register.filter
def asset_url(value):
    """Resolve either a relative asset path or an absolute asset URL."""
    return public_asset_url(value)


@register.simple_tag
def versioned_static(path: str) -> str:
    """Return a static asset URL with a dev-time cache-busting version."""
    url = static(path)
    if not settings.DEBUG:
        return url

    matched_path = finders.find(path)
    if not matched_path:
        return url

    resolved_path = matched_path[0] if isinstance(matched_path, (list, tuple)) else matched_path
    try:
        version = int(Path(resolved_path).stat().st_mtime)
    except OSError:
        return url

    parsed = urlsplit(url)
    query = parsed.query
    version_query = urlencode({"v": version})
    combined_query = f"{query}&{version_query}" if query else version_query
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, combined_query, parsed.fragment))
