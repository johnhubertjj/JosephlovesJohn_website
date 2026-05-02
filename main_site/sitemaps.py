"""Sitemap definitions for the public JosephlovesJohn pages."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .site_data import _get_music_library_items


class StaticViewSitemap(Sitemap):
    """Expose the main public pages and legal routes to search crawlers."""

    def items(self):
        """Return public route metadata for sitemap generation."""
        routes = [
            ("main_site:main", "weekly", 1.0),
            ("main_site:intro", "monthly", 0.7),
            ("main_site:music", "weekly", 0.9),
            ("main_site:art", "monthly", 0.8),
            ("main_site:contact", "monthly", 0.6),
            ("main_site:privacy", "yearly", 0.2),
            ("main_site:cookies", "yearly", 0.2),
            ("main_site:terms", "yearly", 0.2),
            ("main_site:refunds", "yearly", 0.2),
            ("mastering:home", "monthly", 0.5),
        ]
        routes.extend(
            ("main_site:music_track", "weekly", 0.8, {"slug": item["public_slug"]})
            for item in _get_music_library_items()
            if item.get("public_slug")
        )
        return routes

    def location(self, item):
        """Return the route location for the current sitemap item."""
        route_name = item[0]
        kwargs = item[3] if len(item) > 3 else None
        return reverse(route_name, kwargs=kwargs)

    def changefreq(self, item):
        """Return the change frequency for the current sitemap item."""
        return item[1]

    def priority(self, item):
        """Return the priority for the current sitemap item."""
        return item[2]
