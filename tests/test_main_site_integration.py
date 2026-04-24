"""Integration tests for reusable main-site components and rendered flows."""

import pytest
from django.template.loader import render_to_string
from django.test import override_settings
from django.urls import reverse
from main_site import views
from main_site.models import AlbumArt, AnimationAsset, GigPhoto


@pytest.mark.django_db
@pytest.mark.integration
def test_art_route_uses_admin_configured_gig_photo_order(create_static_asset, client) -> None:
    """Database-managed gig photos should drive the rendered gallery order."""
    GigPhoto.objects.all().delete()
    create_static_asset("images/gallery/first.jpg")
    create_static_asset("images/gallery/first-thumb.jpg")
    create_static_asset("images/gallery/first-thumb.webp")
    create_static_asset("images/gallery/second.jpg")
    create_static_asset("images/gallery/inactive.jpg")

    GigPhoto.objects.create(
        title="Second Photo",
        image_path="images/gallery/second.jpg",
        thumbnail_path="",
        alt_text="Second alt",
        sort_order=1,
        is_active=True,
    )
    GigPhoto.objects.create(
        title="Hidden Photo",
        image_path="images/gallery/inactive.jpg",
        thumbnail_path="",
        alt_text="Hidden alt",
        sort_order=5,
        is_active=False,
    )
    GigPhoto.objects.create(
        title="First Photo",
        image_path="images/gallery/first.jpg",
        thumbnail_path="images/gallery/first-thumb.jpg",
        alt_text="First alt",
        sort_order=0,
        is_active=True,
    )

    response = client.get(reverse("main_site:art"))
    body = response.content.decode()

    assert response.context["gig_photo_items"][0]["title"] == "First Photo"
    assert response.context["gig_photo_items"][1]["title"] == "Second Photo"
    assert body.index('data-art-caption="First Photo"') < body.index('data-art-caption="Second Photo"')
    assert 'data-art-caption="Hidden Photo"' not in body
    assert '/static/images/gallery/first-thumb.webp' in body
    assert '/static/images/gallery/first-thumb.jpg' in body


@pytest.mark.django_db
@pytest.mark.integration
def test_art_route_combines_album_art_and_animation_items(create_static_asset, client) -> None:
    """The artwork section should merge album art and animations into one grid."""
    AlbumArt.objects.all().delete()
    AnimationAsset.objects.all().delete()
    create_static_asset("images/album_art/cover.jpg")
    create_static_asset("images/album_art/cover.webp")
    create_static_asset("images/album_art/loop.gif", b"g" * 1000)
    create_static_asset("images/album_art/loop.mp4", b"m" * 100)

    AnimationAsset.objects.create(
        title="Loop Animation",
        file_path="images/album_art/loop.gif",
        sort_order=1,
    )
    AlbumArt.objects.create(
        title="Cover Art",
        image_path="images/album_art/cover.jpg",
        featured=True,
        sort_order=0,
    )

    response = client.get(reverse("main_site:art"))
    body = response.content.decode()

    assert [item["caption"] for item in response.context["album_art_items"]] == ["Cover Art", "Loop Animation"]
    assert body.index("Cover Art") < body.index("Loop Animation")
    assert '/static/images/album_art/cover.webp' in body
    assert '/static/images/album_art/cover.jpg' in body
    assert response.context["album_art_items"][1]["kind"] == "video"
    assert '/static/images/album_art/loop.mp4' in body
    assert 'autoplay' in body
    assert 'loop' in body
    assert 'muted' in body


@pytest.mark.django_db
@pytest.mark.integration
def test_music_route_renders_component_empty_state_when_tracks_are_missing(client, monkeypatch) -> None:
    """The music section should fall back to its reusable empty-state container."""
    monkeypatch.setattr(views, "_get_music_library_items", lambda: [])

    response = client.get(reverse("main_site:music"))
    body = response.content.decode()

    assert response.context["music_items"] == []
    assert "Music is being refreshed. Check back soon." in body
    assert "music-library-item" not in body


@pytest.mark.django_db
@pytest.mark.integration
def test_music_route_replaces_buy_button_for_signed_in_owners(client, django_user_model, monkeypatch) -> None:
    """Signed-in listeners should see an account reminder for tracks they already own."""
    user = django_user_model.objects.create_user(
        username="collector",
        email="collector@example.com",
        password="secret123",
    )
    client.force_login(user)
    monkeypatch.setattr(views, "get_owned_product_slugs", lambda user, *, slugs=None: {slugs[0]})

    response = client.get(reverse("main_site:music"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Already in your account" in body
    assert reverse("shop:account") in body


@pytest.mark.django_db
@pytest.mark.integration
def test_art_route_renders_component_empty_states_when_galleries_are_empty(client, monkeypatch) -> None:
    """The art section should surface both empty states when no gallery items exist."""
    monkeypatch.setattr(views, "_get_gig_photo_items", lambda: [])
    monkeypatch.setattr(views, "_get_album_art_items", lambda: [])

    response = client.get(reverse("main_site:art"))
    body = response.content.decode()

    assert response.context["gig_photo_items"] == []
    assert response.context["album_art_items"] == []
    assert "Gig photos are being refreshed. Check back soon." in body
    assert "Album artwork is being refreshed. Check back soon." in body


@pytest.mark.integration
def test_music_library_item_component_renders_reusable_share_and_player_structure() -> None:
    """The music library item partial should render its reusable container contract."""
    html = render_to_string(
        "main_site/includes/components/music/library_item.html",
        {
            "item": {
                "title": "Reusable Track",
                "meta": "Demo Mix",
                "art_path": "images/album_art/dark_and_light_artist_cover.jpg",
                "art_alt": "Reusable artwork",
                "player_id": "reusable-track-player",
                "file_wav": "audio/reusable-track.wav",
                "file_mp3": "audio/reusable-track.mp3",
                "is_reversed": True,
                "share_path": "/music/",
            }
        },
    )

    assert 'class="music-library-item is-reversed"' in html
    assert 'data-share-title="Reusable Track"' in html
    assert 'data-share-path="/music/"' in html
    assert 'id="reusable-track-player"' in html
    assert 'data-file-mp3="/static/audio/reusable-track.mp3"' in html


@pytest.mark.integration
def test_intro_signup_component_renders_click_to_load_gate() -> None:
    """The intro signup partial should defer Kit until the user explicitly opens it."""
    html = render_to_string("main_site/includes/components/intro/signup_form.html")

    assert 'data-signup-root' in html
    assert 'data-kit-src="https://josephlovesjohn.kit.com/408ee57c19/index.js"' in html
    assert 'data-signup-gate' in html
    assert 'data-analytics-signup-open' in html
    assert 'data-analytics-signup-fallback' in html
    assert "Open signup form" in html
    assert "provided by Kit and may use cookies" in html
    assert 'data-signup-embed' in html


@pytest.mark.django_db
@pytest.mark.integration
@override_settings(
    PLAUSIBLE_DOMAIN="josephlovesjohn.com",
    PLAUSIBLE_SCRIPT_SRC="https://plausible.io/js/pa-example.js",
)
def test_main_site_renders_plausible_snippet_when_enabled(client) -> None:
    """The site shell should render Plausible only when the domain is configured."""
    response = client.get(reverse("main_site:main"))
    body = response.content.decode()

    assert 'data-analytics-enabled="true"' in body
    assert 'src="https://plausible.io/js/pa-example.js"' in body
    assert "window.plausible.init();" in body
    assert '/static/main_site/js/analytics.js' in body


@pytest.mark.integration
def test_gig_photo_grid_component_renders_empty_state() -> None:
    """The gig-photo grid partial should expose a reusable empty-state message."""
    html = render_to_string(
        "main_site/includes/components/art/gig_photo_grid.html",
        {"gig_photo_items": []},
    )

    assert "Gig photos are being refreshed. Check back soon." in html


@pytest.mark.integration
def test_gig_photo_grid_component_renders_direct_urls() -> None:
    """Gig photo cards should render thumbs in the grid and full images in the lightbox link."""
    html = render_to_string(
        "main_site/includes/components/art/gig_photo_grid.html",
        {
            "gig_photo_items": [
                {
                    "title": "Reusable Photo",
                    "image_url": "/media/gig_photos/uploads/reusable.jpg",
                    "thumbnail_url": "/media/gig_photos/thumbs/uploads/reusable-thumb.jpg",
                    "thumbnail_webp_url": "/media/gig_photos/thumbs/uploads/reusable-thumb.webp",
                    "alt_text": "Reusable photo",
                }
            ]
        },
    )

    assert 'href="/media/gig_photos/uploads/reusable.jpg"' in html
    assert 'srcset="/media/gig_photos/thumbs/uploads/reusable-thumb.webp"' in html
    assert 'src="/media/gig_photos/thumbs/uploads/reusable-thumb.jpg"' in html
    assert 'loading="lazy"' in html
    assert 'decoding="async"' in html


@pytest.mark.integration
def test_gig_photo_grid_component_falls_back_to_title_for_missing_alt_text() -> None:
    """Gig photo cards should use the title when no explicit alt text is supplied."""
    html = render_to_string(
        "main_site/includes/components/art/gig_photo_grid.html",
        {
            "gig_photo_items": [
                {
                    "title": "Fallback Gig Photo",
                    "image_url": "/media/gig_photos/uploads/reusable.jpg",
                    "thumbnail_url": "/media/gig_photos/thumbs/uploads/reusable-thumb.jpg",
                    "alt_text": "",
                }
            ]
        },
    )

    assert 'alt="Fallback Gig Photo"' in html


@pytest.mark.integration
def test_album_art_grid_component_renders_featured_and_contain_variants() -> None:
    """The album-art grid partial should render featured cards and contain-fit artwork."""
    html = render_to_string(
        "main_site/includes/components/art/album_art_grid.html",
        {
            "album_art_items": [
                {
                    "kind": "image",
                    "url": "/static/images/album_art/buddlea_animation.gif",
                    "thumbnail_url": "/static/images/album_art/buddlea_animation.gif",
                    "thumbnail_webp_url": "/static/images/album_art/buddlea_animation.webp",
                    "caption": "Buddlea Animation",
                    "alt": "Buddlea animation artwork",
                    "featured": True,
                    "fit_contain": True,
                }
            ]
        },
    )

    assert 'class="album-art-card is-featured"' in html
    assert 'class="is-contain"' in html
    assert 'srcset="/static/images/album_art/buddlea_animation.webp"' in html
    assert "Buddlea Animation" in html


@pytest.mark.integration
def test_album_art_grid_component_renders_looping_animation_video_without_controls() -> None:
    """Auto-upgraded animation videos should loop inline without player chrome."""
    html = render_to_string(
        "main_site/includes/components/art/album_art_grid.html",
        {
            "album_art_items": [
                {
                    "kind": "video",
                    "url": "/static/images/album_art/symbol_animation.mp4",
                    "mime_type": "video/mp4",
                    "caption": "Symbol Animation",
                    "alt": "Symbol animation artwork",
                    "featured": False,
                    "fit_contain": True,
                    "autoplay": True,
                    "loop": True,
                    "muted": True,
                    "show_controls": False,
                    "poster_url": "",
                }
            ]
        },
    )

    assert 'href="/static/images/album_art/symbol_animation.mp4"' in html
    assert 'data-art-lightbox="video"' in html
    assert 'source src="/static/images/album_art/symbol_animation.mp4"' in html
    assert "autoplay" in html
    assert "loop" in html
    assert "muted" in html
    assert 'class="is-contain"' in html
    assert 'data-art-preview-video' in html
    assert 'webkit-playsinline' in html
    assert 'preload="metadata"' in html
    assert "controls" not in html
    assert 'aria-label="Symbol animation artwork"' in html


@pytest.mark.integration
def test_album_art_grid_component_falls_back_to_caption_for_missing_alt_text() -> None:
    """Album-art images should use the caption when no explicit alt text is supplied."""
    html = render_to_string(
        "main_site/includes/components/art/album_art_grid.html",
        {
            "album_art_items": [
                {
                    "kind": "image",
                    "url": "/static/images/album_art/buddlea_animation.gif",
                    "caption": "Fallback Album Art",
                    "alt": "",
                    "featured": False,
                    "fit_contain": False,
                }
            ]
        },
    )

    assert 'alt="Fallback Album Art"' in html


@pytest.mark.integration
def test_header_component_renders_primary_nav_and_social_links() -> None:
    """The header partial should stay reusable with injected nav and social data."""
    html = render_to_string(
        "main_site/includes/layout/header.html",
        {
            "header_social_links": [
                {
                    "href": "https://example.com/bandcamp",
                    "icon_class": "icon brands fa-bandcamp",
                    "label": "Bandcamp",
                },
                {
                    "href": "https://example.com/spotify",
                    "icon_class": "icon brands fa-spotify",
                    "label": "Spotify",
                },
                {
                    "href": "https://example.com/instagram",
                    "icon_class": "icon brands fa-instagram",
                    "label": "Instagram",
                },
            ],
            "primary_nav_items": [
                {"href": "#intro", "label": "Intro"},
                {"href": "#music", "label": "Music"},
                {"href": "#art", "label": "Art"},
            ],
        },
    )

    for link in ("https://example.com/bandcamp", "https://example.com/spotify", "https://example.com/instagram"):
        assert link in html

    assert html.index("Bandcamp") < html.index("Spotify") < html.index("Instagram")

    for label in ("Bandcamp", "Spotify", "Instagram", "Intro", "Music", "Art"):
        assert label in html
