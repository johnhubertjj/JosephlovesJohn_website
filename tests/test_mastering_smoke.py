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
        "Mastering Services",
        "Single, EP, and Album Mastering",
        "A Thoughtful, Song-First Process",
        "What You Receive",
        "Get in touch",
        "Contact via Main Site",
        "Future Subfolder Placeholder",
    ):
        assert text in body


@pytest.mark.integration
def test_mastering_home_from_main_site_sets_transition_class_and_homepage_link(client) -> None:
    """The mastering home page should reflect arrival from the main site."""
    response = client.get(reverse("mastering:home"), {"from_home": "1"})
    body = response.content.decode()

    assert response.context["entered_from_home"] is True
    assert 'class="is-preload is-from-home"' in body
    assert f'href="{reverse("main_site:main")}"' in body
