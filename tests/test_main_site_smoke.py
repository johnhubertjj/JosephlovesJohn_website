"""Smoke tests for the rendered main-site pages and assets."""

import pytest
from django.urls import reverse
from main_site import views

pytestmark = [pytest.mark.django_db, pytest.mark.smoke]


def test_homepage_smoke_renders_layout_navigation_and_social_links(client) -> None:
    """The main site homepage should render the shared shell and navigation."""
    response = client.get(reverse("main_site:main"))
    body = response.content.decode()

    assert response.status_code == 200
    for fragment in (
        'id="top-nav"',
        'id="header"',
        'id="main"',
        'id="footer"',
        'id="music-share-modal"',
        'id="art-lightbox"',
    ):
        assert fragment in body

    for item in views.PRIMARY_NAV_ITEMS:
        assert item["label"] in body
        assert f'href="{item["href"]}"' in body

    for link in views.HEADER_SOCIAL_LINKS:
        assert link["label"] in body
        assert f'href="{link["href"]}"' in body


def test_intro_page_smoke_renders_signup_and_mastering_cta(client) -> None:
    """The intro route should expose the signup group and mastering CTA."""
    response = client.get(reverse("main_site:intro"))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'aria-label="Sign up for updates"' in body
    assert 'id="intro-signup-email"' in body
    assert "Sign up!" in body
    assert f'href="{reverse("mastering:home")}"' in body



def test_music_page_smoke_renders_all_manifest_items_and_share_controls(client) -> None:
    """The music route should render one player row and share trigger per track."""
    response = client.get(reverse("main_site:music"))
    body = response.content.decode()

    assert response.status_code == 200
    assert len(response.context["music_items"]) == len(views.MUSIC_LIBRARY_MANIFEST)
    assert body.count("music-library-item") == len(views.MUSIC_LIBRARY_MANIFEST)
    assert body.count("music-share-trigger") == len(views.MUSIC_LIBRARY_MANIFEST)
    assert body.count("music-player-frame") == len(views.MUSIC_LIBRARY_MANIFEST)

    for item in views.MUSIC_LIBRARY_MANIFEST:
        assert item["title"] in body
        assert item["meta"] in body



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



def test_smoke_manifest_assets_exist_on_disk() -> None:
    """Music and gallery manifests should only point at files that ship with the site."""
    for item in views.MUSIC_LIBRARY_MANIFEST:
        assert views._static_file_exists(item["art_path"])
        assert views._static_file_exists(item["file_wav"])
        assert views._static_file_exists(item["file_mp3"])

    for item in views.DEFAULT_GIG_PHOTO_LIBRARY:
        assert views._static_file_exists(item["image_path"])
        thumbnail = item.get("thumbnail_path")
        if thumbnail:
            assert views._static_file_exists(thumbnail)

    for item in views.ALBUM_ART_MANIFEST:
        assert views._static_file_exists(item["path"])
