"""Application configuration for the main site app."""

from django.apps import AppConfig


class MainSiteConfig(AppConfig):
    """Configure the main site Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "main_site"
