"""Signals for keeping shared main-site cache entries fresh."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import invalidate_shared_content_cache
from .models import AlbumArt, AnimationAsset, GigPhoto, HeaderSocialLink, PrimaryNavItem


@receiver(post_save, sender=HeaderSocialLink)
@receiver(post_delete, sender=HeaderSocialLink)
@receiver(post_save, sender=PrimaryNavItem)
@receiver(post_delete, sender=PrimaryNavItem)
@receiver(post_save, sender=GigPhoto)
@receiver(post_delete, sender=GigPhoto)
@receiver(post_save, sender=AlbumArt)
@receiver(post_delete, sender=AlbumArt)
@receiver(post_save, sender=AnimationAsset)
@receiver(post_delete, sender=AnimationAsset)
def invalidate_main_site_content_cache(**kwargs) -> None:
    """Invalidate shared main-site content whenever admin-managed content changes."""
    del kwargs
    invalidate_shared_content_cache()
