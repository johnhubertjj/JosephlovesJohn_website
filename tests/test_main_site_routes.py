"""Black-box route tests for the main site."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.smoke]


@pytest.mark.parametrize(
    ("route_name", "expected_section", "expected_text"),
    [
        ("main_site:main", "", "Welcome to the main site."),
        ("main_site:intro", "intro", "kept up to date"),
        ("main_site:music", "music", "Dark and Light - Artist Version"),
        ("main_site:art", "art", "Gig Photos"),
        ("main_site:contact", "contact", "Send Message"),
    ],
)
def test_main_site_routes_render_expected_sections(
    client, route_name: str, expected_section: str, expected_text: str
) -> None:
    """Each main-site route should render successfully with the right active section."""
    response = client.get(reverse(route_name))

    assert response.status_code == 200
    assert response.context["active_section"] == expected_section
    assert expected_text in response.content.decode()


def test_music_route_exposes_share_modal_and_player_markup(client) -> None:
    """The music page should include the reusable player/share UI."""
    response = client.get(reverse("main_site:music"))
    body = response.content.decode()

    assert "music-share-modal" in body
    assert "music-cart-modal" in body
    assert "floating-cart-button" in body
    assert "music-player-frame" in body
    assert body.count("music-share-trigger") >= 2
    assert body.count("music-buy-trigger") >= 2


def test_music_track_route_renders_clean_service_link_page(client) -> None:
    """A track page should expose only the artwork/title and ordered service links."""
    response = client.get(reverse("main_site:music_track", args=["dark-and-light-instrumental"]))
    body = response.content.decode()

    assert response.status_code == 200
    assert response.context["active_section"] == "music"
    assert 'href="/">Josephlovesjohn.com</a>' in body
    assert "Dark and Light - Instrumental" in body
    assert "https://open.spotify.com/track/3oUvoKqq4qrlSP5VkCqhvh?si=889a04bcb1bf42b7" in body
    assert "http://itunes.apple.com/album/id1882279580?ls=1&amp;app=itunes" in body
    assert "http://itunes.apple.com/album/id/1882279580" in body
    assert "https://youtu.be/KedziCK2Ct0?si=42uMnyZpIANmINH-" in body
    assert "https://music.amazon.co.uk/albums/B0GR12KXQN?marketplaceId=A1F83G8C2ARO7P" in body
    assert "https://link.deezer.com/s/339jNY0PN3084QcnTPMfA" in body
    assert "https://tidal.com/track/503829268/u" in body
    assert "data-cart-add-url" not in body
    assert "music-player-frame" not in body
    assert "/shop/" not in body
    expected_order = ["Spotify", "iTunes", "Apple Music", "Bandcamp", "YouTube", "Amazon Music", "Deezer", "TIDAL"]
    positions = [body.index(f"<span>{label}</span>") for label in expected_order]
    assert positions == sorted(positions)


def test_music_track_route_supports_canonical_dark_and_light_slug(client) -> None:
    """The public artist-version route should use the shorter SEO-friendly track slug."""
    response = client.get(reverse("main_site:music_track", args=["dark-and-light"]))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Dark and Light - Artist Version" in body
    assert "https://open.spotify.com/track/3oUvoKqq4qrlSP5VkCqhvh?si=c0ea820a417d4845" in body
    assert "http://itunes.apple.com/album/id1870775878?ls=1&amp;app=itunes" in body
    assert "https://music.apple.com/us/song/dark-and-light/1870775884" in body
    assert "https://josephlovesjohn.bandcamp.com/track/dark-and-light" in body
    assert "https://youtu.be/FQHSHiUG_gU?si=r2wMfmQy1e7b86oh" in body
    assert "https://music.amazon.co.uk/albums/B0GHXN25VG?marketplaceId=A1F83G8C2ARO7P" in body
    assert "https://link.deezer.com/s/339jOD96TC9KXp5iQM3d1" in body
    assert response.context["seo"]["canonical_url"].endswith("/music/dark-and-light/")


def test_music_track_route_keeps_old_artist_slug_as_alias(client) -> None:
    """Existing links using the product slug should still resolve to the canonical page."""
    response = client.get(reverse("main_site:music_track", args=["dark-and-light-artist-version"]))

    assert response.status_code == 200
    assert response.context["seo"]["canonical_url"].endswith("/music/dark-and-light/")


def test_unknown_music_track_route_404s(client) -> None:
    """Unknown track slugs should not render a generic music page."""
    response = client.get(reverse("main_site:music_track", args=["not-a-track"]))

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("route_name", "expected_text"),
    [
        ("main_site:privacy", "Privacy Policy"),
        ("main_site:cookies", "Cookies Policy"),
        ("main_site:terms", "Terms of Sale"),
        ("main_site:refunds", "Refunds and Digital Downloads"),
    ],
)
def test_legal_routes_render(client, route_name: str, expected_text: str) -> None:
    """Legal-information pages should render successfully."""
    response = client.get(reverse(route_name))

    assert response.status_code == 200
    assert expected_text in response.content.decode()


def test_legal_routes_use_empty_cart_summary_context(client) -> None:
    """Pages without cart UI should not do full cart-summary work."""
    response = client.get(reverse("main_site:privacy"))

    assert response.status_code == 200
    assert response.context["cart_summary"]["is_empty"] is True
    assert response.context["cart_summary"]["item_count"] == 0
