"""Tests for the main site model and admin configuration."""

import pytest
from django.contrib import admin
from django.core.exceptions import ValidationError
from main_site.admin import (
    AlbumArtAdmin,
    AnimationAssetAdmin,
    GigPhotoAdmin,
    HeaderSocialLinkAdmin,
    PrimaryNavItemAdmin,
)
from main_site.models import AlbumArt, AnimationAsset, GigPhoto, HeaderSocialLink, PrimaryNavItem

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
def test_header_social_link_string_representation_uses_label() -> None:
    """Header social links should use their label in admin contexts."""
    link = HeaderSocialLink.objects.create(
        label="Bandcamp",
        href="https://example.com/bandcamp",
        icon_class="icon brands fa-bandcamp",
    )

    assert str(link) == "Bandcamp"


@pytest.mark.django_db
def test_primary_nav_item_string_representation_uses_label() -> None:
    """Primary nav items should use their label in admin contexts."""
    item = PrimaryNavItem.objects.create(label="Music", href="#music")

    assert str(item) == "Music"


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


@pytest.mark.django_db
def test_header_social_links_default_ordering_is_sort_order_then_id() -> None:
    """Header social links should be returned in display order."""
    HeaderSocialLink.objects.all().delete()
    HeaderSocialLink.objects.create(label="Third", href="https://example.com/3", icon_class="icon-3", sort_order=2)
    HeaderSocialLink.objects.create(label="First", href="https://example.com/1", icon_class="icon-1", sort_order=0)
    HeaderSocialLink.objects.create(label="Second", href="https://example.com/2", icon_class="icon-2", sort_order=1)

    labels = list(HeaderSocialLink.objects.values_list("label", flat=True))

    assert labels == ["First", "Second", "Third"]


@pytest.mark.django_db
def test_primary_nav_items_default_ordering_is_sort_order_then_id() -> None:
    """Primary nav items should be returned in display order."""
    PrimaryNavItem.objects.all().delete()
    PrimaryNavItem.objects.create(label="Third", href="#third", sort_order=2)
    PrimaryNavItem.objects.create(label="First", href="#first", sort_order=0)
    PrimaryNavItem.objects.create(label="Second", href="#second", sort_order=1)

    labels = list(PrimaryNavItem.objects.values_list("label", flat=True))

    assert labels == ["First", "Second", "Third"]


def test_header_social_link_admin_configuration_matches_header_workflow() -> None:
    """Header social link admin should support sorting and searching."""
    admin_instance = HeaderSocialLinkAdmin(HeaderSocialLink, admin.site)

    assert admin_instance.list_display == ("label", "sort_order", "is_active", "href", "icon_class")
    assert admin_instance.list_editable == ("sort_order", "is_active")
    assert admin_instance.search_fields == ("label", "href", "icon_class")
    assert admin_instance.ordering == ("sort_order", "id")


def test_primary_nav_item_admin_configuration_matches_navigation_workflow() -> None:
    """Primary nav admin should support sorting and searching."""
    admin_instance = PrimaryNavItemAdmin(PrimaryNavItem, admin.site)

    assert admin_instance.list_display == ("label", "sort_order", "is_active", "href")
    assert admin_instance.list_editable == ("sort_order", "is_active")
    assert admin_instance.search_fields == ("label", "href")
    assert admin_instance.ordering == ("sort_order", "id")


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


@pytest.mark.parametrize(
    ("asset", "message"),
    [
        (GigPhoto(title="Missing gig photo"), "Add either an image upload or a static image path."),
        (AlbumArt(title="Missing album art"), "Add either an image upload or a static image path."),
        (AnimationAsset(title="Missing animation"), "Add either an animation upload or a static file path."),
    ],
)
def test_gallery_assets_require_a_file_source(asset, message: str) -> None:
    """Gallery assets should validate that a path or upload has been supplied."""
    with pytest.raises(ValidationError, match=message):
        asset.clean()
