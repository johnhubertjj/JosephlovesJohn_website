"""Sitemap definitions for the public JosephlovesJohn pages."""

from typing import NamedTuple

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .site_data import _get_music_library_items


class SitemapRoute(NamedTuple):
    """Route metadata used by the public sitemap."""

    route_name: str
    change_frequency: str
    route_priority: float
    kwargs: dict[str, object] | None = None


class StaticViewSitemap(Sitemap):
    """Expose the main public pages and legal routes to search crawlers."""

    def items(self):
        """Return public route metadata for sitemap generation."""
        routes = [
            SitemapRoute("main_site:main", "weekly", 1.0),
            SitemapRoute("main_site:intro", "monthly", 0.7),
            SitemapRoute("main_site:music", "weekly", 0.9),
            SitemapRoute("main_site:art", "monthly", 0.8),
            SitemapRoute("main_site:contact", "monthly", 0.6),
            SitemapRoute("main_site:privacy", "yearly", 0.2),
            SitemapRoute("main_site:cookies", "yearly", 0.2),
            SitemapRoute("main_site:terms", "yearly", 0.2),
            SitemapRoute("main_site:refunds", "yearly", 0.2),
            SitemapRoute("mastering:home", "monthly", 0.5),
        ]
        routes.extend(
            SitemapRoute("main_site:music_track", "weekly", 0.8, {"slug": item["public_slug"]})
            for item in _get_music_library_items()
            if item.get("public_slug")
        )
        return routes

    def location(self, item):
        """Return the route location for the current sitemap item."""
        return reverse(item.route_name, kwargs=item.kwargs)

    def changefreq(self, item):
        """Return the change frequency for the current sitemap item."""
        return item.change_frequency

    def priority(self, item):
        """Return the priority for the current sitemap item."""
        return item.route_priority
