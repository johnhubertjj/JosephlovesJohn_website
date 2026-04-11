"""Black-box route tests for the mastering site."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.smoke


def test_mastering_home_renders_default_context(client) -> None:
    """The mastering homepage should render and default the transition flag to false."""
    response = client.get(reverse("mastering:home"))

    assert response.status_code == 200
    assert response.context["entered_from_home"] is False
    assert "Mastering Services" in response.content.decode()


def test_mastering_home_marks_requests_arriving_from_main_site(client) -> None:
    """The query-string flag should be exposed in the template context."""
    response = client.get(reverse("mastering:home"), {"from_home": "1"})

    assert response.status_code == 200
    assert response.context["entered_from_home"] is True


def test_mastering_subfolder_renders_requested_slug(client) -> None:
    """Placeholder mastering subfolders should display the requested slug."""
    response = client.get(reverse("mastering:subfolder", args=["future-folder"]))
    body = response.content.decode()

    assert response.status_code == 200
    assert response.context["subfolder"] == "future-folder"
    assert "future-folder" in body
