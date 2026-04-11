"""Black-box tests for main site helper functions."""

from unittest.mock import Mock

import pytest
from django.db import OperationalError
from main_site import views
from main_site.models import GigPhoto


@pytest.mark.django_db
def test_get_gig_photo_items_prefers_active_database_rows(create_static_asset, monkeypatch) -> None:
    """Database-backed active photos should be returned in display order."""
    create_static_asset("images/gallery/live-1.jpg")
    create_static_asset("images/gallery/live-1-thumb.jpg")
    create_static_asset("images/gallery/live-2.jpg")

    GigPhoto.objects.create(
        title="Later",
        image_path="images/gallery/live-2.jpg",
        thumbnail_path="",
        alt_text="Later alt",
        sort_order=20,
        is_active=True,
    )
    GigPhoto.objects.create(
        title="Hidden",
        image_path="images/gallery/hidden.jpg",
        thumbnail_path="",
        alt_text="Hidden alt",
        sort_order=5,
        is_active=False,
    )
    GigPhoto.objects.create(
        title="Earlier",
        image_path="images/gallery/live-1.jpg",
        thumbnail_path="images/gallery/live-1-thumb.jpg",
        alt_text="Earlier alt",
        sort_order=10,
        is_active=True,
    )

    monkeypatch.setattr(views.settings, "BASE_DIR", views.settings.BASE_DIR, raising=False)
    items = views._get_gig_photo_items()

    assert [item["title"] for item in items] == ["Earlier", "Later"]
    assert items[0]["thumbnail_path"] == "images/gallery/live-1-thumb.jpg"
    assert items[1]["thumbnail_path"] == "images/gallery/live-2.jpg"


def test_normalize_static_path_strips_prefixes() -> None:
    """Static paths should be normalized for the helper layer."""
    assert views._normalize_static_path("/static/images/example.jpg") == "images/example.jpg"
    assert views._normalize_static_path(" static/images/example.jpg ") == "images/example.jpg"
    assert views._normalize_static_path("images/example.jpg") == "images/example.jpg"


def test_build_gig_photo_item_falls_back_to_source_image_when_thumb_missing(create_static_asset, monkeypatch) -> None:
    """Gallery items should still render if a thumbnail is missing."""
    create_static_asset("images/gig_photos/test-photo.jpg")
    monkeypatch.setattr(views.settings, "BASE_DIR", views.settings.BASE_DIR, raising=False)

    item = views._build_gig_photo_item(
        title="Test Photo",
        image_path="static/images/gig_photos/test-photo.jpg",
        thumbnail_path="images/gig_photos/missing-thumb.jpg",
        alt_text="",
    )

    assert item == {
        "title": "Test Photo",
        "image_path": "images/gig_photos/test-photo.jpg",
        "thumbnail_path": "images/gig_photos/test-photo.jpg",
        "alt_text": "Test Photo",
    }


def test_get_album_art_items_filters_missing_assets_and_sets_video_mime(create_static_asset, monkeypatch) -> None:
    """Album art entries should only include items whose assets are present."""
    create_static_asset("images/album_art/cover.jpg")
    create_static_asset("images/album_art/animation.mp4")
    monkeypatch.setattr(
        views,
        "ALBUM_ART_MANIFEST",
        (
            {
                "kind": "image",
                "path": "images/album_art/cover.jpg",
                "caption": "Cover",
                "alt": "Cover art",
                "featured": True,
            },
            {
                "kind": "image",
                "path": "images/album_art/missing.jpg",
                "caption": "Missing",
                "alt": "Missing",
                "featured": False,
            },
            {
                "kind": "video",
                "path": "images/album_art/animation.mp4",
                "caption": "Animation",
                "alt": "Animation",
                "featured": False,
                "poster": "images/album_art/missing-poster.jpg",
            },
        ),
    )
    monkeypatch.setattr(views.settings, "BASE_DIR", views.settings.BASE_DIR, raising=False)

    items = views._get_album_art_items()

    assert [item["caption"] for item in items] == ["Cover", "Animation"]
    assert items[1]["mime_type"] == "video/mp4"
    assert items[1]["poster"] == ""


@pytest.mark.django_db
def test_get_gig_photo_items_falls_back_to_manifest_when_database_lookup_fails(
    create_static_asset, monkeypatch
) -> None:
    """Static manifest items should be used when the database is unavailable."""
    create_static_asset("images/fallback/one.jpg")
    create_static_asset("images/fallback/two.jpg")
    monkeypatch.setattr(
        views,
        "DEFAULT_GIG_PHOTO_LIBRARY",
        (
            {"title": "Fallback One", "image_path": "images/fallback/one.jpg", "thumbnail_path": "", "alt_text": "One"},
            {"title": "Fallback Two", "image_path": "images/fallback/two.jpg", "thumbnail_path": "", "alt_text": "Two"},
        ),
    )

    broken_filter = Mock(side_effect=OperationalError("db unavailable"))
    monkeypatch.setattr(views.GigPhoto.objects, "filter", broken_filter)
    monkeypatch.setattr(views.settings, "BASE_DIR", views.settings.BASE_DIR, raising=False)

    items = views._get_gig_photo_items()

    assert [item["title"] for item in items] == ["Fallback One", "Fallback Two"]
    broken_filter.assert_called_once_with(is_active=True)


def test_get_music_library_items_adds_music_route_share_path() -> None:
    """Music library items should include the reusable music share route."""
    items = views._get_music_library_items()
    expected_titles = [manifest_item["title"] for manifest_item in views.MUSIC_LIBRARY_MANIFEST]

    assert items
    assert {item["share_path"] for item in items} == {"/music/"}
    assert [item["title"] for item in items] == expected_titles


def test_site_context_collects_expected_sections(monkeypatch) -> None:
    """The site context should gather all renderable page sections."""
    monkeypatch.setattr(views, "_get_music_library_items", lambda: [{"title": "Song"}])
    monkeypatch.setattr(views, "_get_gig_photo_items", lambda: [{"title": "Photo"}])
    monkeypatch.setattr(views, "_get_album_art_items", lambda: [{"caption": "Art"}])

    context = views._site_context("music")

    assert context["active_section"] == "music"
    assert context["music_items"] == [{"title": "Song"}]
    assert context["gig_photo_items"] == [{"title": "Photo"}]
    assert context["album_art_items"] == [{"caption": "Art"}]
    assert context["primary_nav_items"] == views.PRIMARY_NAV_ITEMS
    assert context["header_social_links"] == views.HEADER_SOCIAL_LINKS
