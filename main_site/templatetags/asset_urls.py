"""Template helpers for resolving static/CDN asset URLs."""

from django import template
from josephlovesjohn_site.assets import public_asset_url

register = template.Library()


@register.filter
def asset_url(value):
    """Resolve either a relative asset path or an absolute asset URL."""
    return public_asset_url(value)
