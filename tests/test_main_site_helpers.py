"""Black-box tests for main site helper functions."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.db import OperationalError
from django.test import override_settings
from josephlovesjohn_site import assets
from main_site import cache as main_site_cache
from main_site import views
from main_site.models import AlbumArt, AnimationAsset, GigPhoto, HeaderSocialLink, PrimaryNavItem
from shop.models import Product

pytestmark = pytest.mark.integration


@pytest.mark.django_db
def test_get_header_social_links_returns_active_database_rows_in_order() -> None:
    """Header links should be sourced from the database in display order."""
    HeaderSocialLink.objects.all().delete()
    HeaderSocialLink.objects.create(
        label="YouTube",
        href="https://example.com/youtube",
        icon_class="icon brands fa-youtube",
        sort_order=1,
        is_active=True,
    )
    HeaderSocialLink.objects.create(
        label="Hidden",
        href="https://example.com/hidden",
        icon_class="icon brands fa-hidden",
        sort_order=0,
        is_active=False,
    )
    HeaderSocialLink.objects.create(
        label="Bandcamp",
        href="https://example.com/bandcamp",
        icon_class="icon brands fa-bandcamp",
        sort_order=0,
        is_active=True,
    )

    links = views._get_header_social_links()

    assert links == [
        {
            "href": "https://example.com/bandcamp",
            "icon_class": "icon brands fa-bandcamp",
            "label": "Bandcamp",
        },
        {
            "href": "https://open.spotify.com/artist/27YZiLsfuwfBI5e4BZyTIi?si=rcYZFzPzSPCfartpPGM6gg",
            "icon_class": "icon brands fa-spotify",
            "label": "Spotify",
        },
        {
            "href": "https://example.com/youtube",
            "icon_class": "icon brands fa-youtube",
            "label": "YouTube",
        },
    ]


@pytest.mark.django_db
def test_get_header_social_links_moves_spotify_to_second_position() -> None:
    """Spotify should always render immediately after Bandcamp."""
    HeaderSocialLink.objects.all().delete()
    HeaderSocialLink.objects.create(
        label="Bandcamp",
        href="https://example.com/bandcamp",
        icon_class="icon brands fa-bandcamp",
        sort_order=0,
        is_active=True,
    )
    HeaderSocialLink.objects.create(
        label="Spotify",
        href="https://example.com/old-spotify",
        icon_class="icon brands fa-spotify",
        sort_order=4,
        is_active=True,
    )
    HeaderSocialLink.objects.create(
        label="Instagram",
        href="https://example.com/instagram",
        icon_class="icon brands fa-instagram",
        sort_order=1,
        is_active=True,
    )

    links = views._get_header_social_links()

    assert [link["label"] for link in links] == ["Bandcamp", "Spotify", "Instagram"]
    assert links[1]["href"] == "https://open.spotify.com/artist/27YZiLsfuwfBI5e4BZyTIi?si=rcYZFzPzSPCfartpPGM6gg"


@pytest.mark.django_db
def test_get_primary_nav_items_returns_active_database_rows_in_order() -> None:
    """Primary nav items should be sourced from the database in display order."""
    PrimaryNavItem.objects.all().delete()
    PrimaryNavItem.objects.create(label="Art", href="#art", sort_order=2, is_active=True)
    PrimaryNavItem.objects.create(label="Hidden", href="#hidden", sort_order=0, is_active=False)
    PrimaryNavItem.objects.create(label="Intro", href="#intro", sort_order=0, is_active=True)
    PrimaryNavItem.objects.create(label="Music", href="#music", sort_order=1, is_active=True)

    items = views._get_primary_nav_items()

    assert items == [
        {"href": "#intro", "label": "Intro"},
        {"href": "#music", "label": "Music"},
        {"href": "#art", "label": "Art"},
    ]


@pytest.mark.django_db
@override_settings(SITE_CONTENT_CACHE_TTL=60)
def test_get_header_social_links_cache_invalidates_when_content_changes() -> None:
    """Shared site-content cache should refresh when admin-managed content changes."""
    cache.clear()
    HeaderSocialLink.objects.all().delete()
    HeaderSocialLink.objects.create(
        label="Bandcamp",
        href="https://example.com/bandcamp",
        icon_class="icon brands fa-bandcamp",
        sort_order=0,
        is_active=True,
    )

    first_links = views._get_header_social_links()

    HeaderSocialLink.objects.create(
        label="YouTube",
        href="https://example.com/youtube",
        icon_class="icon brands fa-youtube",
        sort_order=1,
        is_active=True,
    )
    refreshed_links = views._get_header_social_links()

    assert [link["label"] for link in first_links] == ["Bandcamp", "Spotify"]
    assert [link["label"] for link in refreshed_links] == ["Bandcamp", "Spotify", "YouTube"]


@override_settings(SITE_CONTENT_CACHE_TTL=60)
def test_shared_content_cache_context_reuses_version_lookup_per_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """One request should only fetch the shared-content cache version once."""
    version_calls = {"count": 0}

    def fake_get(key, default=None):
        if key == main_site_cache._VERSION_KEY:
            version_calls["count"] += 1
            return 7
        return default

    monkeypatch.setattr(main_site_cache.cache, "get", fake_get)

    middleware = main_site_cache.SharedContentCacheContextMiddleware(
        lambda request: HttpResponse(
            f"{main_site_cache._content_cache_version()}:{main_site_cache._content_cache_version()}"
        )
    )

    response = middleware(SimpleNamespace())

    assert response.content.decode() == "7:7"
    assert version_calls["count"] == 1


@pytest.mark.django_db
def test_get_gig_photo_items_prefers_active_database_rows(create_static_asset) -> None:
    """Database-backed active photos should be returned in display order."""
    GigPhoto.objects.all().delete()
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


@pytest.mark.django_db
@override_settings(SITE_CONTENT_CACHE_TTL=60)
def test_get_gig_photo_items_does_not_reuse_cached_empty_results(monkeypatch, create_static_asset) -> None:
    """Transient empty gig-photo results should not get stuck in shared cache."""
    cache.clear()
    GigPhoto.objects.all().delete()
    create_static_asset("images/gallery/live-1.jpg")
    photo = GigPhoto.objects.create(
        title="Recovered Photo",
        image_path="images/gallery/live-1.jpg",
        alt_text="Recovered alt",
        sort_order=0,
        is_active=True,
    )

    original_filter = views.GigPhoto.objects.filter
    calls = {"count": 0}

    def flaky_filter(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OperationalError("temporary db issue")
        return original_filter(*args, **kwargs)

    monkeypatch.setattr(views.GigPhoto.objects, "filter", flaky_filter)

    first_items = views._get_gig_photo_items()
    second_items = views._get_gig_photo_items()

    assert first_items == []
    assert second_items == [
        {
            "title": photo.title,
            "image_path": photo.image_path,
            "thumbnail_path": photo.image_path,
            "image_url": "/static/images/gallery/live-1.jpg",
            "thumbnail_url": "/static/images/gallery/live-1.jpg",
            "alt_text": photo.alt_text,
        }
    ]


def test_normalize_asset_path_strips_prefixes() -> None:
    """Static paths should be normalized consistently by the shared asset helpers."""
    assert assets.normalize_asset_path("/static/images/example.jpg") == "images/example.jpg"
    assert assets.normalize_asset_path(" static/images/example.jpg ") == "images/example.jpg"
    assert assets.normalize_asset_path("images/example.jpg") == "images/example.jpg"


def test_uploaded_file_exists_returns_false_without_a_usable_name() -> None:
    """Uploaded-file checks should fail closed when no file name is available."""
    assert views._uploaded_file_exists(None) is False
    assert views._uploaded_file_exists(SimpleNamespace(name="")) is False


def test_uploaded_file_exists_returns_false_when_storage_errors() -> None:
    """Uploaded-file checks should fail closed when storage lookups error."""
    storage = Mock()
    storage.exists.side_effect = OSError("storage unavailable")
    file_field = SimpleNamespace(name="uploads/test.jpg", storage=storage)

    assert views._uploaded_file_exists(file_field) is False


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


def test_resolve_asset_source_supports_external_urls() -> None:
    """Absolute asset URLs should be returned directly without static lookup."""
    url = "https://assets.example.com/images/gig_photos/live.jpg"

    assert views._resolve_asset_source(static_path=url) == {
        "path": url,
        "url": url,
        "is_static": False,
    }


@override_settings(PUBLIC_ASSET_BASE_URL="https://assets.example.com")
def test_resolve_asset_source_uses_public_asset_base_url_without_local_static_file() -> None:
    """Gallery items should resolve through the CDN even when the file is not in the repo."""
    assert views._resolve_asset_source(static_path="images/gig_photos/live.jpg") == {
        "path": "images/gig_photos/live.jpg",
        "url": "https://assets.example.com/images/gig_photos/live.jpg",
        "is_static": True,
    }


@pytest.mark.django_db
def test_get_album_art_items_combines_album_art_and_animations(create_static_asset) -> None:
    """Album art entries should combine still artwork and animations in sort order."""
    AlbumArt.objects.all().delete()
    AnimationAsset.objects.all().delete()
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
def test_get_music_library_items_uses_published_products_in_order() -> None:
    """Music library items should be sourced from the product catalog."""
    Product.objects.all().delete()
    Product.objects.create(
        title="Second Track",
        slug="second-track",
        meta="Single",
        art_path="images/album_art/second.jpg",
        preview_file_wav="audio/second.wav",
        preview_file_mp3="audio/second.mp3",
        download_file_path="audio/second.mp3",
        sort_order=1,
        is_published=True,
        is_reversed=True,
    )
    Product.objects.create(
        title="Hidden Track",
        slug="hidden-track",
        meta="Hidden",
        art_path="images/album_art/hidden.jpg",
        preview_file_wav="audio/hidden.wav",
        preview_file_mp3="audio/hidden.mp3",
        download_file_path="audio/hidden.mp3",
        sort_order=0,
        is_published=False,
    )
    Product.objects.create(
        title="First Track",
        slug="first-track",
        meta="EP",
        art_path="images/album_art/first.jpg",
        preview_file_wav="audio/first.wav",
        preview_file_mp3="audio/first.mp3",
        download_file_path="audio/first.mp3",
        sort_order=0,
        is_published=True,
        is_reversed=False,
    )

    items = views._get_music_library_items()

    assert [item["title"] for item in items] == ["First Track", "Second Track"]
    assert {item["share_path"] for item in items} == {"/music/"}
    assert all(item["buy_path"].startswith("/shop/cart/add/") for item in items)
    assert items[0]["art_url"] == "/static/images/album_art/first.jpg"
    assert items[0]["file_wav_url"] == "/static/audio/first.wav"
    assert items[0]["file_mp3_url"] == "/static/audio/first.mp3"
    assert items[1]["is_reversed"] is True


@pytest.mark.django_db
@override_settings(SITE_CONTENT_CACHE_TTL=60)
def test_get_music_library_items_cache_invalidates_when_products_change() -> None:
    """Shared music-library cache should refresh after product changes."""
    cache.clear()
    Product.objects.all().delete()
    Product.objects.create(
        title="First Track",
        slug="first-track",
        meta="Single",
        art_path="images/album_art/first.jpg",
        preview_file_wav="audio/first.wav",
        preview_file_mp3="audio/first.mp3",
        download_file_path="audio/first.mp3",
        sort_order=0,
        is_published=True,
    )

    first_items = views._get_music_library_items()

    Product.objects.create(
        title="Second Track",
        slug="second-track",
        meta="Single",
        art_path="images/album_art/second.jpg",
        preview_file_wav="audio/second.wav",
        preview_file_mp3="audio/second.mp3",
        download_file_path="audio/second.mp3",
        sort_order=1,
        is_published=True,
    )
    refreshed_items = views._get_music_library_items()

    assert [item["title"] for item in first_items] == ["First Track"]
    assert [item["title"] for item in refreshed_items] == ["First Track", "Second Track"]


@pytest.mark.django_db
def test_get_header_social_links_returns_empty_when_database_lookup_fails(monkeypatch) -> None:
    """Header links should fail closed when the database is unavailable."""
    monkeypatch.setattr(views.HeaderSocialLink.objects, "filter", Mock(side_effect=OperationalError("db unavailable")))

    assert views._get_header_social_links() == []


@pytest.mark.django_db
def test_get_primary_nav_items_returns_empty_when_database_lookup_fails(monkeypatch) -> None:
    """Primary nav should fail closed when the database is unavailable."""
    monkeypatch.setattr(views.PrimaryNavItem.objects, "filter", Mock(side_effect=OperationalError("db unavailable")))

    assert views._get_primary_nav_items() == []


@pytest.mark.django_db
def test_get_gig_photo_items_returns_empty_when_database_lookup_fails(monkeypatch) -> None:
    """Gig photo helpers should fail closed when the database is unavailable."""
    monkeypatch.setattr(views.GigPhoto.objects, "filter", Mock(side_effect=OperationalError("db unavailable")))

    assert views._get_gig_photo_items() == []


@pytest.mark.django_db
def test_get_album_art_items_returns_empty_when_database_lookup_fails(monkeypatch) -> None:
    """Album art helpers should fail closed when the database is unavailable."""
    monkeypatch.setattr(views.AlbumArt.objects, "filter", Mock(side_effect=OperationalError("db unavailable")))

    assert views._get_album_art_items() == []


@pytest.mark.django_db
def test_get_music_library_items_returns_empty_when_database_lookup_fails(monkeypatch) -> None:
    """Music helpers should fail closed when the database is unavailable."""
    monkeypatch.setattr(views.Product.objects, "filter", Mock(side_effect=OperationalError("db unavailable")))

    assert views._get_music_library_items() == []


def test_site_context_collects_expected_sections(monkeypatch) -> None:
    """The site context should gather all renderable page sections."""
    monkeypatch.setattr(views, "_get_header_social_links", lambda: [{"label": "Bandcamp"}])
    monkeypatch.setattr(views, "_get_primary_nav_items", lambda: [{"label": "Music"}])
    monkeypatch.setattr(views, "_get_music_library_items", lambda: [{"title": "Song"}])
    monkeypatch.setattr(views, "_get_gig_photo_items", lambda: [{"title": "Photo"}])
    monkeypatch.setattr(views, "_get_album_art_items", lambda: [{"caption": "Art"}])

    context = views._site_context("music")

    assert context["active_section"] == "music"
    assert context["header_social_links"] == [{"label": "Bandcamp"}]
    assert context["primary_nav_items"] == [{"label": "Music"}]
    assert context["music_items"] == [{"title": "Song"}]
    assert context["gig_photo_items"] == [{"title": "Photo"}]
    assert context["album_art_items"] == [{"caption": "Art"}]
