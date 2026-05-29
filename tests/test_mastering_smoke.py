"""Smoke and integration tests for the mastering site shell."""

import pytest
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
        "Further Release Consultations",
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
    assert "mastering-example-dark-and-light.jpg" in body
    assert "mastering-example-super-dungeon.jpg" in body
    assert body.count('class="mastering-example-player"') == 2
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


@pytest.mark.integration
def test_mastering_home_from_main_site_sets_transition_class_and_homepage_link(client) -> None:
    """The mastering home page should reflect arrival from the main site."""
    response = client.get(reverse("mastering:home"), {"from_home": "1"})
    body = response.content.decode()

    assert response.context["entered_from_home"] is True
    assert 'class="is-preload is-from-home"' in body
    assert f'href="{reverse("main_site:main")}"' in body
