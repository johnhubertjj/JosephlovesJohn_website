"""Accessibility-oriented rendering checks for shared interactive UI."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.integration]



def test_music_route_renders_labeled_share_modal_controls(client) -> None:
    """The music page should expose accessible labels for the share and cart modal controls."""
    response = client.get(reverse("main_site:music"))
    body = response.content.decode()

    assert 'role="dialog"' in body
    assert 'aria-modal="true"' in body
    assert 'aria-label="Close share dialog"' in body
    assert 'aria-label="Copy share link"' in body
    assert 'aria-label="Share on Threads"' in body
    assert 'aria-label="Share on Facebook"' in body
    assert 'aria-label="Share on X"' in body
    assert 'aria-label="Share by email"' in body
    assert 'aria-label="Close cart"' in body
    assert 'aria-label="Open cart"' in body



def test_art_and_contact_routes_render_accessible_labels(client) -> None:
    """Art lightbox controls and contact fields should render with user-facing labels."""
    art_response = client.get(reverse("main_site:art"))
    art_body = art_response.content.decode()
    contact_response = client.get(reverse("main_site:contact"))
    contact_body = contact_response.content.decode()

    assert 'aria-label="Expanded artwork"' in art_body
    assert 'aria-label="Close expanded artwork"' in art_body

    for label in (
        "<label for=\"name\">Name</label>",
        "<label for=\"email\">Email</label>",
        "<label for=\"message\">Message</label>",
    ):
        assert label in contact_body
