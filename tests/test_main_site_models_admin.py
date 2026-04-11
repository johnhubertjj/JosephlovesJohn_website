"""Tests for the main site model and admin configuration."""

import pytest
from django.contrib import admin
from main_site.admin import GigPhotoAdmin
from main_site.models import GigPhoto


@pytest.mark.django_db
def test_gig_photo_string_representation_uses_title() -> None:
    """Gig photo labels should match their title in admin/UI contexts."""
    photo = GigPhoto.objects.create(
        title="Live at Bristol",
        image_path="images/gig_photos/live.jpg",
        thumbnail_path="",
        alt_text="Live photo",
    )

    assert str(photo) == "Live at Bristol"


@pytest.mark.django_db
def test_gig_photo_default_ordering_is_sort_order_then_id() -> None:
    """Gig photos should be returned in the gallery's configured order."""
    GigPhoto.objects.create(title="Ordering Third", image_path="three.jpg", sort_order=30)
    GigPhoto.objects.create(title="Ordering First", image_path="one.jpg", sort_order=10)
    GigPhoto.objects.create(title="Ordering Second", image_path="two.jpg", sort_order=20)

    titles = list(
        GigPhoto.objects.filter(title__startswith="Ordering").values_list("title", flat=True)
    )

    assert titles == ["Ordering First", "Ordering Second", "Ordering Third"]


def test_gig_photo_admin_configuration_matches_gallery_workflow() -> None:
    """Admin options should support sorting, toggling, and searching photos."""
    admin_instance = GigPhotoAdmin(GigPhoto, admin.site)

    assert admin_instance.list_display == ("title", "sort_order", "is_active", "image_path", "thumbnail_path")
    assert admin_instance.list_editable == ("sort_order", "is_active")
    assert admin_instance.search_fields == ("title", "image_path", "thumbnail_path", "alt_text")
    assert admin_instance.ordering == ("sort_order", "id")
