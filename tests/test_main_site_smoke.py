"""Smoke tests for the rendered main-site pages and assets."""

import pytest
from django.urls import reverse
from main_site import views
from main_site.models import AlbumArt, GigPhoto, HeaderSocialLink, PrimaryNavItem
from shop.models import Product

pytestmark = [pytest.mark.django_db, pytest.mark.smoke]


def test_homepage_smoke_renders_layout_navigation_and_social_links(client) -> None:
    """The main site homepage should render the shared shell and navigation."""
    response = client.get(reverse("main_site:main"))
    body = response.content.decode()

    assert response.status_code == 200
    for fragment in (
        'id="header"',
        'id="main"',
        'id="footer"',
        'rel="icon"',
        'data-cookie-banner',
        'data-cookie-essential-only',
        'data-cookie-accept-all',
        'id="music-share-modal"',
        'id="music-cart-modal"',
        'id="floating-cart-button"',
        'id="art-lightbox"',
    ):
        assert fragment in body

    for route_name in ("main_site:privacy", "main_site:cookies", "main_site:terms", "main_site:refunds"):
        assert f'href="{reverse(route_name)}"' in body

    assert 'data-cookie-manage' in body

    for item in response.context["primary_nav_items"]:
        assert item["label"] in body
        assert f'href="{item["href"]}"' in body

    for link in response.context["header_social_links"]:
        assert link["label"] in body
        assert f'href="{link["href"]}"' in body

    assert '/static/images/jlovesj_symbol-my_version3.png' in body


def test_intro_page_smoke_renders_signup_and_mastering_cta(client) -> None:
    """The intro route should expose the delayed signup form gate and mastering CTA."""
    response = client.get(reverse("main_site:intro"))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'aria-label="Sign up for updates"' in body
    assert 'data-signup-root' in body
    assert 'data-kit-src="https://josephlovesjohn.kit.com/408ee57c19/index.js"' in body
    assert 'data-signup-gate' in body
    assert "Open signup form" in body
    assert 'href="https://josephlovesjohn.kit.com/408ee57c19"' in body
    assert f'href="{reverse("mastering:home")}"' in body


def test_music_page_smoke_renders_all_published_tracks_and_share_controls(client) -> None:
    """The music route should render one player row and share trigger per track."""
    response = client.get(reverse("main_site:music"))
    body = response.content.decode()

    expected_items = list(Product.objects.filter(is_published=True).order_by("sort_order", "id"))

    assert response.status_code == 200
    assert len(response.context["music_items"]) == len(expected_items)
    assert body.count("music-library-item") == len(expected_items)
    assert body.count("music-share-trigger") == len(expected_items)
    assert body.count("music-buy-trigger") == len(expected_items)
    assert body.count("music-player-frame") == len(expected_items)

    for item in expected_items:
        assert item.title in body
        assert item.meta in body


def test_art_page_smoke_renders_split_gallery_and_lightbox_triggers(client) -> None:
    """The art route should render both gallery blocks and image lightbox triggers."""
    response = client.get(reverse("main_site:art"))
    body = response.content.decode()

    expected_lightbox_items = len(response.context["gig_photo_items"]) + sum(
        1 for item in response.context["album_art_items"] if item["kind"] == "image"
    )

    assert response.status_code == 200
    assert "Gig Photos" in body
    assert "Album &amp; Assorted Artwork" in body
    assert "picturemover" in body
    assert body.count('data-art-lightbox="image"') == expected_lightbox_items
    assert 'aria-label="Expanded artwork"' in body


def test_contact_page_smoke_renders_labeled_form_controls(client) -> None:
    """The contact route should render a labeled message form."""
    response = client.get(reverse("main_site:contact"))
    body = response.content.decode()

    assert response.status_code == 200
    for label in ("Name", "Email", "Message", "Send Message", "Reset"):
        assert label in body

    for field_id in ("name", "email", "message"):
        assert f'id="{field_id}"' in body


def test_smoke_database_backed_assets_exist_on_disk_with_mock_media(create_static_asset) -> None:
    """DB-backed asset checks should work against synthetic static media in CI."""
    Product.objects.all().delete()
    GigPhoto.objects.all().delete()
    AlbumArt.objects.all().delete()
    HeaderSocialLink.objects.all().delete()
    PrimaryNavItem.objects.all().delete()

    product = Product.objects.create(
        title="Mock Song",
        slug="mock-song",
        meta="Single",
        art_path=create_static_asset("images/album_art/mock-song-cover.jpg"),
        art_alt="Mock cover art",
        preview_file_wav=create_static_asset("audio/mock-song.wav"),
        preview_file_mp3=create_static_asset("audio/mock-song.mp3"),
        download_file_path="audio/mock-song.mp3",
        sort_order=0,
        is_published=True,
    )
    gig_photo = GigPhoto.objects.create(
        title="Mock Gig",
        image_path=create_static_asset("images/gig_photos/mock-gig.jpeg"),
        thumbnail_path=create_static_asset("images/gig_photos/thumbs/mock-gig-thumb.jpg"),
        alt_text="Mock gig photo",
    )
    album_art = AlbumArt.objects.create(
        title="Mock Gallery Art",
        image_path=create_static_asset("images/album_art/mock-gallery-art.gif"),
        alt_text="Mock gallery artwork",
        featured=True,
    )

    items = views._get_music_library_items()
    gig_items = views._get_gig_photo_items()
    album_items = views._get_album_art_items()

    assert items[0]["title"] == product.title
    assert views._static_file_exists(items[0]["art_path"])
    assert views._static_file_exists(items[0]["file_wav"])
    assert views._static_file_exists(items[0]["file_mp3"])

    assert gig_items[0]["title"] == gig_photo.title
    assert views._static_file_exists(gig_items[0]["image_path"])
    assert views._static_file_exists(gig_items[0]["thumbnail_path"])

    assert album_items[0]["caption"] == album_art.title
    assert views._static_file_exists(album_items[0]["path"])
