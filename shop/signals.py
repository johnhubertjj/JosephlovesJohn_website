"""Signals for storefront cache invalidation."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from main_site.cache import invalidate_shared_content_cache

from .models import Product


@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_storefront_content_cache(**kwargs) -> None:
    """Invalidate shared main-site content whenever published products change."""
    del kwargs
    invalidate_shared_content_cache()
