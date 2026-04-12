"""Black-box tests for main site helper functions."""

from unittest.mock import Mock

import pytest
from django.core.files.base import ContentFile
from django.db import OperationalError
from main_site import views
from main_site.models import AlbumArt, AnimationAsset, GigPhoto

pytestmark = pytest.mark.integration


@pytest.mark.django_db
def test_get_gig_photo_items_prefers_active_database_rows(create_static_asset) -> None:
    """Database-backed active photos should be returned in display order."""
    create_static_asset("images/gallery/live-1.jpg")
    create_static_asset("images/gallery/live-1-thumb.jpg")
    create_static_asset("images/gallery/live-2.jpg")

    GigPhoto.objects.create(
        title="Later",
        image_path="images/gallery/live-2.jpg",
        thumbnail_path="",
        alt_text="Later alt",
        sort_order=1,
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
        sort_order=0,
        is_active=True,
    )

    items = views._get_gig_photo_items()

    assert [item["title"] for item in items] == ["Earlier", "Later"]
    assert items[0]["thumbnail_path"] == "images/gallery/live-1-thumb.jpg"
    assert items[0]["thumbnail_url"] == "/static/images/gallery/live-1-thumb.jpg"
    assert items[1]["thumbnail_path"] == "images/gallery/live-2.jpg"
    assert items[1]["thumbnail_url"] == "/static/images/gallery/live-2.jpg"


@pytest.mark.django_db
def test_get_gig_photo_items_supports_uploaded_files(media_base_dir) -> None:
    """Uploaded gig photos should render through media URLs."""
    GigPhoto.objects.all().delete()
    photo = GigPhoto.objects.create(title="Uploaded Photo", alt_text="Uploaded alt", sort_order=0)
    photo.image_file.save("live.jpg", ContentFile(b"live"), save=True)
    photo.thumbnail_file.save("live-thumb.jpg", ContentFile(b"thumb"), save=True)

    items = views._get_gig_photo_items()

    assert items == [
        {
            "title": "Uploaded Photo",
            "image_path": photo.image_file.name,
            "thumbnail_path": photo.thumbnail_file.name,
            "image_url": f"/media/{photo.image_file.name}",
            "thumbnail_url": f"/media/{photo.thumbnail_file.name}",
            "alt_text": "Uploaded alt",
        }
    ]


def test_normalize_static_path_strips_prefixes() -> None:
    """Static paths should be normalized for the helper layer."""
    assert views._normalize_static_path("/static/images/example.jpg") == "images/example.jpg"
    assert views._normalize_static_path(" static/images/example.jpg ") == "images/example.jpg"
    assert views._normalize_static_path("images/example.jpg") == "images/example.jpg"


def test_build_gig_photo_item_falls_back_to_source_image_when_thumb_missing(create_static_asset) -> None:
    """Gallery items should still render if a thumbnail is missing."""
    create_static_asset("images/gig_photos/test-photo.jpg")

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
        "image_url": "/static/images/gig_photos/test-photo.jpg",
        "thumbnail_url": "/static/images/gig_photos/test-photo.jpg",
        "alt_text": "Test Photo",
    }


@pytest.mark.django_db
def test_get_album_art_items_combines_album_art_and_animations(create_static_asset) -> None:
    """Album art entries should combine still artwork and animations in sort order."""
    create_static_asset("images/album_art/cover.jpg")
    create_static_asset("images/album_art/animation.mp4")
    create_static_asset("images/album_art/poster.jpg")

    AnimationAsset.objects.create(
        title="Animation",
        media_kind=AnimationAsset.MediaKind.VIDEO,
        file_path="images/album_art/animation.mp4",
        poster_path="images/album_art/poster.jpg",
        sort_order=1,
    )
    AlbumArt.objects.create(
        title="Cover",
        image_path="images/album_art/cover.jpg",
        alt_text="Cover art",
        featured=True,
        sort_order=0,
    )

    items = views._get_album_art_items()

    assert [item["caption"] for item in items] == ["Cover", "Animation"]
    assert items[0]["url"] == "/static/images/album_art/cover.jpg"
    assert items[1]["mime_type"] == "video/mp4"
    assert items[1]["poster_url"] == "/static/images/album_art/poster.jpg"


@pytest.mark.django_db
def test_get_album_art_items_supports_uploaded_files(media_base_dir) -> None:
    """Uploaded album art and animation files should render through media URLs."""
    AlbumArt.objects.all().delete()
    AnimationAsset.objects.all().delete()
    art = AlbumArt.objects.create(title="Uploaded Cover", featured=True, sort_order=0)
    art.image_file.save("cover.jpg", ContentFile(b"cover"), save=True)

    animation = AnimationAsset.objects.create(
        title="Uploaded Animation",
        media_kind=AnimationAsset.MediaKind.IMAGE,
        sort_order=1,
    )
    animation.file_upload.save("loop.gif", ContentFile(b"gif"), save=True)

    items = views._get_album_art_items()

    assert [item["caption"] for item in items] == ["Uploaded Cover", "Uploaded Animation"]
    assert items[0]["url"] == f"/media/{art.image_file.name}"
    assert items[1]["url"] == f"/media/{animation.file_upload.name}"


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

    items = views._get_gig_photo_items()

    assert [item["title"] for item in items] == ["Fallback One", "Fallback Two"]
    broken_filter.assert_called_once_with(is_active=True)


def test_get_album_art_items_falls_back_to_manifest_when_database_lookup_fails(
    create_static_asset, monkeypatch
) -> None:
    """Static manifest items should be used when the artwork tables are unavailable."""
    create_static_asset("images/album_art/fallback-cover.jpg")
    create_static_asset("images/album_art/fallback-animation.gif")
    monkeypatch.setattr(
        views,
        "ALBUM_ART_MANIFEST",
        (
            {
                "kind": "image",
                "path": "images/album_art/fallback-cover.jpg",
                "caption": "Fallback Cover",
                "alt": "Fallback cover art",
                "featured": True,
            },
            {
                "kind": "image",
                "path": "images/album_art/fallback-animation.gif",
                "caption": "Fallback Animation",
                "alt": "Fallback animation",
                "featured": False,
            },
        ),
    )

    monkeypatch.setattr(views.AlbumArt.objects, "filter", Mock(side_effect=OperationalError("db unavailable")))

    items = views._get_album_art_items()

    assert [item["caption"] for item in items] == ["Fallback Cover", "Fallback Animation"]


def test_get_music_library_items_adds_music_route_share_path() -> None:
    """Music library items should include the reusable music share route."""
    items = views._get_music_library_items()
    expected_titles = [manifest_item["title"] for manifest_item in views.MUSIC_LIBRARY_MANIFEST]

    assert items
    assert {item["share_path"] for item in items} == {"/music/"}
    assert all(item["buy_path"].startswith("/shop/cart/add/") for item in items)
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
