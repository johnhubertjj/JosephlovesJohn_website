"""Tests for the main site model and admin configuration."""

import pytest
from django.contrib import admin
from main_site.admin import AlbumArtAdmin, AnimationAssetAdmin, GigPhotoAdmin
from main_site.models import AlbumArt, AnimationAsset, GigPhoto

pytestmark = pytest.mark.integration


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
    GigPhoto.objects.create(title="Ordering Third", image_path="three.jpg", sort_order=2)
    GigPhoto.objects.create(title="Ordering First", image_path="one.jpg", sort_order=0)
    GigPhoto.objects.create(title="Ordering Second", image_path="two.jpg", sort_order=1)

    titles = list(
        GigPhoto.objects.filter(title__startswith="Ordering").values_list("title", flat=True)
    )

    assert titles == ["Ordering First", "Ordering Second", "Ordering Third"]


@pytest.mark.django_db
def test_album_art_default_ordering_is_sort_order_then_id() -> None:
    """Album art should use the same ascending sort-order behavior."""
    AlbumArt.objects.all().delete()
    AlbumArt.objects.create(title="Album Third", image_path="three.jpg", sort_order=2)
    AlbumArt.objects.create(title="Album First", image_path="one.jpg", sort_order=0)
    AlbumArt.objects.create(title="Album Second", image_path="two.jpg", sort_order=1)

    titles = list(AlbumArt.objects.values_list("title", flat=True))

    assert titles == ["Album First", "Album Second", "Album Third"]


@pytest.mark.django_db
def test_animation_default_ordering_is_sort_order_then_id() -> None:
    """Animations should use the same ascending sort-order behavior."""
    AnimationAsset.objects.all().delete()
    AnimationAsset.objects.create(title="Anim Third", file_path="three.gif", sort_order=2)
    AnimationAsset.objects.create(title="Anim First", file_path="one.gif", sort_order=0)
    AnimationAsset.objects.create(title="Anim Second", file_path="two.gif", sort_order=1)

    titles = list(AnimationAsset.objects.values_list("title", flat=True))

    assert titles == ["Anim First", "Anim Second", "Anim Third"]


def test_gig_photo_admin_configuration_matches_gallery_workflow() -> None:
    """Admin options should support sorting, toggling, searching, and uploads."""
    admin_instance = GigPhotoAdmin(GigPhoto, admin.site)

    assert admin_instance.list_display == (
        "title",
        "sort_order",
        "is_active",
        "image_path",
        "image_file",
        "thumbnail_path",
        "thumbnail_file",
    )
    assert admin_instance.list_editable == ("sort_order", "is_active")
    assert admin_instance.search_fields == (
        "title",
        "image_path",
        "thumbnail_path",
        "alt_text",
        "image_file",
        "thumbnail_file",
    )
    assert admin_instance.ordering == ("sort_order", "id")


def test_album_art_admin_configuration_matches_gallery_workflow() -> None:
    """Album art admin should expose sorting, toggles, and uploads."""
    admin_instance = AlbumArtAdmin(AlbumArt, admin.site)

    assert admin_instance.list_display == (
        "title",
        "sort_order",
        "is_active",
        "featured",
        "image_path",
        "image_file",
    )
    assert admin_instance.list_editable == ("sort_order", "is_active", "featured")
    assert admin_instance.ordering == ("sort_order", "id")


def test_animation_admin_configuration_matches_gallery_workflow() -> None:
    """Animation admin should expose media-type aware controls."""
    admin_instance = AnimationAssetAdmin(AnimationAsset, admin.site)

    assert admin_instance.list_display == (
        "title",
        "media_kind",
        "sort_order",
        "is_active",
        "featured",
        "file_path",
        "file_upload",
    )
    assert admin_instance.list_editable == ("sort_order", "is_active", "featured")
    assert admin_instance.ordering == ("sort_order", "id")
