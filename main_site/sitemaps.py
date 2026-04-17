"""Sitemap definitions for the public JosephlovesJohn pages."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Expose the main public pages and legal routes to search crawlers."""

    def items(self):
        """Return public route metadata for sitemap generation."""
        return [
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

    def location(self, item):
        """Return the route location for the current sitemap item."""
        route_name, _, _ = item
        return reverse(route_name)

    def changefreq(self, item):
        """Return the change frequency for the current sitemap item."""
        _, frequency, _ = item
        return frequency

    def priority(self, item):
        """Return the priority for the current sitemap item."""
        _, _, priority = item
        return priority
