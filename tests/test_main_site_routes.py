"""Black-box route tests for the main site."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.smoke]


@pytest.mark.parametrize(
    ("route_name", "expected_section", "expected_text"),
    [
        ("main_site:main", "", "Welcome to the main site."),
        ("main_site:intro", "intro", "Sign up!"),
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
    assert "music-player-frame" in body
    assert body.count("music-share-trigger") >= 2
