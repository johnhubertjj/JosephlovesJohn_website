"""Smoke and integration tests for the mastering site shell."""

import pytest
from django.test import override_settings
from django.urls import reverse


@pytest.mark.smoke
def test_mastering_home_smoke_renders_menu_sections_and_contact_cta(client) -> None:
    """The mastering landing page should expose its core marketing sections."""
    response = client.get(reverse("mastering:home"))
    body = response.content.decode()

    assert response.status_code == 200
    for text in (
        "John Joseph Mastering",
        "First single master is free!",
        "Contact below",
        "Single, EP, and Album Mastering",
        "Typical turnaround:",
        "3-7 days depending on project size.",
        "A Thoughtful, Song-First Process",
        "Mastering Examples",
        "Dark and Light (Instrumental)",
        "Super Dungeon",
        "Fumebreather",
        'aria-label="Listen to on Spotify"',
        'aria-label="Listen to on Bandcamp"',
        "fa-spotify",
        "fa-bandcamp",
        "What You Receive",
        "Get in touch",
        "Pricing",
        "First Single Master",
        "Free!",
        "If you are a new client, the first single track master is on me.",
        "Master + Release Walkthrough",
        "FAQ",
        "What software do you use?",
        "What is WAV or AIFF?",
        "What is an ISRC code?",
        "What is bit depth?",
        "Send Message",
    ):
        assert text in body
    assert "£50" in body
    assert "£90" in body
    assert "Further Release Consultations" not in body
    assert "mastering-example-dark-and-light.webp" in body
    assert "mastering-example-super-dungeon.webp" in body
    assert 'rel="preload" as="image"' in body
    assert "mastering/images/mastering-website-header-image.webp" in body
    assert body.count('class="mastering-example-player-shell"') == 2
    assert body.count('data-src="https://w.soundcloud.com/player/') == 2
    assert body.count('class="mastering-example-player"') == 2
    assert body.count("<iframe") == 2
    assert 'loading="lazy"' in body
    assert 'decoding="async"' in body
    assert "https://w.soundcloud.com/player/" in body
    assert "url=https%3A//api.soundcloud.com/tracks/soundcloud%253Atracks%253A2254324949" in body
    assert "url=https%3A//soundcloud.com/josephlovesjohn_mastering/mastering_showreel" in body
    spotify_url = "https://open.spotify.com/track/3oUvoKqq4qrlSP5VkCqhvh?si=889a04bcb1bf42b7"
    bandcamp_url = "https://fumebreather.bandcamp.com/album/super-dungeon"
    assert spotify_url in body
    assert bandcamp_url in body
    assert 'href="#contact" class="button primary"' in body
    assert f'href="{spotify_url}"\n                            class="mastering-example-cover"' in body
    assert f'href="{bandcamp_url}"\n                            class="mastering-example-cover"' in body
    assert 'href="https://on.soundcloud.com/55O97EKK0mPpSfjWQF"' not in body
    assert ">Listen<" not in body
    assert body.index('id="examples"') < body.index('id="contact"')
    assert body.index('id="contact"') < body.index('id="pricing"')
    assert body.index('id="pricing"') < body.index('id="services"')
    assert body.index('id="services"') < body.index('id="process"')
    assert body.index('id="process"') < body.index('id="faq"')
    assert 'action="/mastering-services/#contact"' in body
    assert 'data-recaptcha-action="contact"' in body
    assert '<meta name="description"' in body
    assert 'href="http://127.0.0.1:8000/mastering-services/"' in body


@pytest.mark.smoke
@override_settings(RECAPTCHA_SITE_KEY="site-key", RECAPTCHA_SECRET_KEY="secret-key")
def test_mastering_home_lazy_loads_recaptcha_when_enabled(client) -> None:
    """The mastering contact form should avoid the eager reCAPTCHA network request."""
    response = client.get(reverse("mastering:home"))
    body = response.content.decode()

    assert 'data-recaptcha-action="contact"' in body
    assert 'name="g-recaptcha-response"' in body
    assert '<script src="https://www.google.com/recaptcha/api.js?render=site-key"' not in body
    assert "shouldLazyLoad = true" in body
    assert "document.createElement(\"script\")" in body


@pytest.mark.integration
def test_mastering_home_from_main_site_sets_transition_class_and_homepage_link(client) -> None:
    """The mastering home page should reflect arrival from the main site."""
    response = client.get(reverse("mastering:home"), {"from_home": "1"})
    body = response.content.decode()

    assert response.context["entered_from_home"] is True
    assert 'class="is-preload is-from-home"' in body
    assert f'href="{reverse("main_site:main")}"' in body


@pytest.mark.smoke
@override_settings(PUBLIC_ASSET_BASE_URL="https://assets.example.com")
def test_mastering_home_resolves_images_against_public_asset_base_url(client) -> None:
    """Mastering page images should be CDN-ready when a public asset base URL is configured."""
    response = client.get(reverse("mastering:home"))
    body = response.content.decode()

    assert "https://assets.example.com/mastering/images/mastering-website-header-image.webp" in body
    assert "https://assets.example.com/mastering/images/john-joseph-profile.webp" in body
    assert response.context["seo"]["image_url"] == (
        "https://assets.example.com/mastering/images/mastering-website-header-image.webp"
    )
