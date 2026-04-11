"""Application configuration for the mastering app."""

from django.apps import AppConfig


class MasteringConfig(AppConfig):
    """Configure the mastering services Django application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "mastering"
