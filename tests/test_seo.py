"""Tests for search discovery endpoints such as robots.txt and sitemap.xml."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.smoke, pytest.mark.integration]


def test_robots_txt_exposes_sitemap(client) -> None:
    """Robots should allow crawling and point search engines at the sitemap."""
    response = client.get(reverse("robots_txt"))
    body = response.content.decode()

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Sitemap: http://127.0.0.1:8000/sitemap.xml" in body


def test_sitemap_lists_public_pages(client) -> None:
    """The sitemap should expose the main public routes for search discovery."""
    response = client.get(reverse("sitemap"))
    body = response.content.decode()

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/xml")
    assert "http://testserver/music/" in body
    assert "http://testserver/music/dark-and-light/" in body
    assert "http://testserver/music/dark-and-light-instrumental/" in body
    assert "http://testserver/art/" in body
    assert "http://testserver/privacy/" in body
    assert "http://testserver/mastering-services/" in body
