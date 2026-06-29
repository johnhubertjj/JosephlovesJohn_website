"""Black-box route tests for the mastering site."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.smoke


def test_mastering_home_renders_default_context(client) -> None:
    """The mastering homepage should render and default the transition flag to false."""
    response = client.get(reverse("mastering:home"))

    assert response.status_code == 200
    assert response.context["entered_from_home"] is False
    assert "John Joseph Mastering" in response.content.decode()


def test_mastering_home_marks_requests_arriving_from_main_site(client) -> None:
    """The query-string flag should be exposed in the template context."""
    response = client.get(reverse("mastering:home"), {"from_home": "1"})

    assert response.status_code == 200
    assert response.context["entered_from_home"] is True


def test_mastering_intake_renders_form(client) -> None:
    """The mastering intake form should be available as a separate route."""
    response = client.get(reverse("mastering:intake"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Mastering Intake Form" in body
    assert "Are you an artist or engineer?" in body
    assert "I am the artist" in body
    assert "I am the mix engineer" in body
    assert "Contact email" in body
    assert "Mix file link" in body
    assert "What is the sample rate?" in body
    assert "What is the bit depth?" in body
    assert "What is the peak loudness level?" in body
    assert "Artist track upload" in body
    assert "What is the Genre/vibe you are looking for?" in body
    assert "How should the final master feel?" in body
    assert "Is this a hard deadline?" in body
    assert 'name="deadline"' in body
    assert 'type="date"' in body
    assert 'id="footer"' in body
    assert "&copy; JosephlovesJohn. All rights reserved." in body
    assert 'data-recaptcha-action="mastering_intake"' in body


def test_mastering_subfolder_renders_requested_slug(client) -> None:
    """Placeholder mastering subfolders should display the requested slug."""
    response = client.get(reverse("mastering:subfolder", args=["future-folder"]))
    body = response.content.decode()

    assert response.status_code == 200
    assert response.context["subfolder"] == "future-folder"
    assert "future-folder" in body
