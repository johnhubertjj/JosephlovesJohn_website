"""Admin registrations for the main site app."""

from django.contrib import admin

from .models import AlbumArt, AnimationAsset, GigPhoto


class OrderedGalleryAssetAdmin(admin.ModelAdmin):
    """Shared admin configuration for gallery asset collections."""

    list_editable = ("sort_order", "is_active")
    ordering = ("sort_order", "id")


@admin.register(GigPhoto)
class GigPhotoAdmin(OrderedGalleryAssetAdmin):
    """Expose gig photo content controls in the Django admin."""

    list_display = (
        "title",
        "sort_order",
        "is_active",
        "image_path",
        "image_file",
        "thumbnail_path",
        "thumbnail_file",
    )
    search_fields = ("title", "image_path", "thumbnail_path", "alt_text", "image_file", "thumbnail_file")


@admin.register(AlbumArt)
class AlbumArtAdmin(OrderedGalleryAssetAdmin):
    """Expose album artwork controls in the Django admin."""

    list_display = ("title", "sort_order", "is_active", "featured", "image_path", "image_file")
    list_editable = ("sort_order", "is_active", "featured")
    search_fields = ("title", "image_path", "alt_text", "image_file")


@admin.register(AnimationAsset)
class AnimationAssetAdmin(OrderedGalleryAssetAdmin):
    """Expose animation artwork controls in the Django admin."""

    list_display = ("title", "media_kind", "sort_order", "is_active", "featured", "file_path", "file_upload")
    list_editable = ("sort_order", "is_active", "featured")
    search_fields = ("title", "file_path", "poster_path", "alt_text", "file_upload", "poster_upload")
