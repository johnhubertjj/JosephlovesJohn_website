"""Regression tests for refactored static asset paths."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.templatetags.static import static as static_url
from django.urls import reverse

pytestmark = pytest.mark.smoke

_CSS_URL_PATTERN = re.compile(r"url\((?P<quote>['\"]?)(?P<path>[^)\"']+)(?P=quote)\)")
_CSS_IMPORT_PATTERN = re.compile(r"@import url\((?P<quote>['\"]?)(?P<path>[^)\"']+)(?P=quote)\)")


def _iter_css_asset_paths(css_path: Path) -> list[str]:
    """Return file-backed URL and import paths from a CSS file."""
    content = css_path.read_text()
    asset_paths: list[str] = []

    for pattern in (_CSS_URL_PATTERN, _CSS_IMPORT_PATTERN):
        for match in pattern.finditer(content):
            path = match.group("path").strip()
            if not path or path.startswith(("data:", "http://", "https://")):
                continue
            asset_paths.append(path)

    return asset_paths


def _normalize_asset_path(path: str) -> str:
    """Strip CSS URL query strings and fragments before filesystem checks."""
    return path.split("?", 1)[0].split("#", 1)[0]


def test_refactored_vendor_css_assets_resolve_to_real_files() -> None:
    """Moved vendor CSS files should keep valid relative links to their assets."""
    dimension_css = Path(settings.BASE_DIR) / "static" / "assets" / "css" / "vendor" / "dimension.css"
    dimension_assets = _iter_css_asset_paths(dimension_css)
    assert dimension_assets, f"No asset paths found in {dimension_css}"

    for relative_asset in dimension_assets:
        resolved = (dimension_css.parent / _normalize_asset_path(relative_asset)).resolve()
        assert resolved.exists(), f"{dimension_css} points to missing asset {relative_asset}"

    fontawesome_css = Path(settings.BASE_DIR) / "static" / "assets" / "css" / "vendor" / "fontawesome-all.min.css"
    fontawesome_content = fontawesome_css.read_text()
    expected_font_paths = (
        "../../webfonts/fa-brands-400.woff2",
        "../../webfonts/fa-regular-400.woff2",
        "../../webfonts/fa-solid-900.woff2",
    )

    for relative_asset in expected_font_paths:
        assert relative_asset in fontawesome_content
        resolved = (fontawesome_css.parent / relative_asset).resolve()
        assert resolved.exists(), f"{fontawesome_css} points to missing asset {relative_asset}"


@pytest.mark.django_db
def test_main_site_base_template_uses_refactored_asset_locations(client) -> None:
    """The rendered page should reference the reorganized CSS entrypoints."""
    response = client.get(reverse("main_site:main"))
    body = response.content.decode()

    expected_stylesheets = (
        static_url("assets/css/vendor/dimension.css"),
        static_url("assets/css/layout/top-nav.css"),
        static_url("assets/css/layout/header.css"),
        static_url("assets/css/layout/header-nav.css"),
        static_url("assets/css/layout/footer.css"),
        static_url("main_site/css/site.css"),
    )

    for stylesheet in expected_stylesheets:
        assert stylesheet in body
