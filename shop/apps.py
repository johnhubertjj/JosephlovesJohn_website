"""Application configuration for the shop app."""

from django.apps import AppConfig


class ShopConfig(AppConfig):
    """Configure the reusable shop application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"

    def ready(self) -> None:
        """Register signal handlers for cache invalidation."""
        from . import signals  # noqa: F401
