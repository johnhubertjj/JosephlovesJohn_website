"""Admin registrations for the main site app."""

from django.contrib import admin

from .models import GigPhoto


@admin.register(GigPhoto)
class GigPhotoAdmin(admin.ModelAdmin):
    """Expose gig photo content controls in the Django admin."""

    list_display = ("title", "sort_order", "is_active", "image_path", "thumbnail_path")
    list_editable = ("sort_order", "is_active")
    search_fields = ("title", "image_path", "thumbnail_path", "alt_text")
    ordering = ("sort_order", "id")
