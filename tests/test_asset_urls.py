"""Tests for static/CDN asset URL helpers."""

from pathlib import Path

import pytest
from django.test import override_settings
from django.urls import reverse
from josephlovesjohn_site import assets
from main_site.templatetags import asset_urls as asset_url_tags
from shop import models as shop_models
from shop.models import Order, OrderItem, Product


def test_public_asset_url_returns_external_urls_unchanged() -> None:
    """Absolute URLs should bypass static-file lookup."""
    url = "https://cdn.example.com/audio/song.mp3"

    assert assets.public_asset_url(url) == url


def test_resolve_public_asset_source_returns_external_urls_unchanged() -> None:
    """Absolute asset URLs should resolve without static-file checks."""
    url = "https://cdn.example.com/audio/song.mp3"

    assert assets.resolve_public_asset_source(url) == {
        "path": url,
        "url": url,
        "is_static": False,
    }


def test_resolve_public_asset_source_uses_file_exists_callback() -> None:
    """Repo-backed static assets should resolve through the shared helper."""
    assert assets.resolve_public_asset_source(
        "/static/images/cover.jpg",
        file_exists=lambda path: path == "images/cover.jpg",
    ) == {
        "path": "images/cover.jpg",
        "url": "/static/images/cover.jpg",
        "is_static": True,
    }


def test_resolve_public_asset_source_returns_none_when_file_is_missing() -> None:
    """Missing local assets should fail closed when no CDN base URL is configured."""
    assert assets.resolve_public_asset_source(
        "images/missing.jpg",
        file_exists=lambda path: False,
    ) is None


@override_settings(DEBUG=False, VERIFY_STATIC_ASSET_FILES=False, STATIC_URL="/static/")
def test_resolve_public_asset_source_skips_file_checks_outside_debug() -> None:
    """Production-style requests should trust configured static paths without stat calls."""
    file_exists_called = {"called": False}

    def file_exists(path: str) -> bool:
        file_exists_called["called"] = True
        return False

    assert assets.resolve_public_asset_source("images/cover.jpg", file_exists=file_exists) == {
        "path": "images/cover.jpg",
        "url": "/static/images/cover.jpg",
        "is_static": True,
    }
    assert file_exists_called["called"] is False


@override_settings(DEBUG=False, VERIFY_STATIC_ASSET_FILES=True)
def test_resolve_public_asset_source_can_force_file_checks_outside_debug() -> None:
    """Production can opt back into strict repo-file validation when desired."""
    assert assets.resolve_public_asset_source(
        "images/missing.jpg",
        file_exists=lambda path: False,
    ) is None


@override_settings(PUBLIC_ASSET_BASE_URL="https://assets.example.com")
def test_public_asset_url_uses_public_asset_base_url_for_relative_paths() -> None:
    """Relative paths should resolve against the configured public asset base URL."""
    assert assets.public_asset_url("audio/song.mp3") == "https://assets.example.com/audio/song.mp3"
    assert assets.public_asset_url("/static/images/cover.jpg") == "https://assets.example.com/images/cover.jpg"


@override_settings(PUBLIC_ASSET_BASE_URL="https://assets.example.com")
def test_resolve_public_asset_source_uses_public_asset_base_url_without_file_check() -> None:
    """Configured CDN-backed assets should resolve even if the file is not in the repo."""
    assert assets.resolve_public_asset_source("images/cover.jpg") == {
        "path": "images/cover.jpg",
        "url": "https://assets.example.com/images/cover.jpg",
        "is_static": True,
    }


@override_settings(STATIC_URL="/static/")
def test_public_asset_url_falls_back_when_manifest_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing manifest entries should not crash production renders."""
    monkeypatch.setattr(assets, "static_url", lambda path: (_ for _ in ()).throw(ValueError("missing manifest")))

    assert assets.public_asset_url("images/gig_photos/test.jpg") == "/static/images/gig_photos/test.jpg"


@override_settings(DEBUG=True)
def test_versioned_static_appends_mtime_in_debug(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Debug static asset URLs should be cache-busted with the local file mtime."""
    asset_path = tmp_path / "site.js"
    asset_path.write_text("console.log('hello');", encoding="utf-8")
    monkeypatch.setattr(asset_url_tags, "static", lambda path: f"/static/{path}")
    monkeypatch.setattr(asset_url_tags.finders, "find", lambda path: str(asset_path))

    versioned_url = asset_url_tags.versioned_static("main_site/js/site.js")

    assert versioned_url == f"/static/main_site/js/site.js?v={int(asset_path.stat().st_mtime)}"


@override_settings(DEBUG=False)
def test_versioned_static_uses_plain_static_url_outside_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production/static-manifest mode should leave the asset URL unchanged."""
    monkeypatch.setattr(asset_url_tags, "static", lambda path: f"/static/{path}")

    assert asset_url_tags.versioned_static("main_site/js/site.js") == "/static/main_site/js/site.js"


@pytest.mark.django_db
def test_product_asset_properties_support_external_urls() -> None:
    """Shop products should expose public URLs for CDN-hosted files."""
    product = Product.objects.create(
        title="External Track",
        slug="external-track",
        art_path="https://cdn.example.com/images/cover.jpg",
        preview_file_wav="https://cdn.example.com/audio/preview.wav",
        preview_file_mp3="https://cdn.example.com/audio/preview.mp3",
        download_file_path="https://cdn.example.com/audio/full.mp3",
        download_file_wav_path="https://cdn.example.com/audio/full.wav",
    )

    assert product.art_url == "https://cdn.example.com/images/cover.jpg"
    assert product.preview_wav_url == "https://cdn.example.com/audio/preview.wav"
    assert product.preview_mp3_url == "https://cdn.example.com/audio/preview.mp3"
    assert product.download_url == "https://cdn.example.com/audio/full.mp3"
    assert product.download_wav_url == "https://cdn.example.com/audio/full.wav"


@pytest.mark.django_db
def test_product_preview_urls_can_use_private_signed_assets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Music-page previews should use signed private URLs when configured."""
    product = Product.objects.create(
        title="Private Preview Track",
        slug="private-preview-track",
        art_path="images/album_art/cover.jpg",
        preview_file_wav="audio/private-preview.wav",
        preview_file_mp3="audio/private-preview.mp3",
        download_file_path="audio/private-download.mp3",
    )

    monkeypatch.setattr(
        shop_models,
        "preview_asset_url",
        lambda path: f"https://signed.example.com/{path}",
    )

    assert product.preview_wav_url == "https://signed.example.com/audio/private-preview.wav"
    assert product.preview_mp3_url == "https://signed.example.com/audio/private-preview.mp3"


@pytest.mark.django_db
@override_settings(PUBLIC_ASSET_BASE_URL="https://assets.example.com")
def test_order_item_urls_split_public_art_and_protected_download_route() -> None:
    """Existing order snapshots should keep public art but use app download routes."""
    product = Product.objects.create(
        title="Track",
        slug="track",
        art_path="images/album_art/cover.jpg",
        preview_file_wav="audio/track.wav",
        preview_file_mp3="audio/track.mp3",
        download_file_path="audio/track.mp3",
        download_file_wav_path="audio/track.wav",
    )
    order = Order.objects.create(
        full_name="Listener",
        email="listener@example.com",
        subtotal="1.00",
        total="1.00",
    )
    item = OrderItem.objects.create(
        order=order,
        product=product,
        title_snapshot="Track",
        artist_snapshot="JosephlovesJohn",
        meta_snapshot="Single",
        price_snapshot="1.00",
        art_path_snapshot="images/album_art/cover.jpg",
        art_alt_snapshot="Cover",
        download_file_path="audio/track.mp3",
        download_file_wav_path="audio/track.wav",
    )

    assert item.art_url == "https://assets.example.com/images/album_art/cover.jpg"
    assert item.download_url == reverse("shop:download", kwargs={"item_id": item.pk})
    assert item.download_wav_url == f'{reverse("shop:download", kwargs={"item_id": item.pk})}?format=wav'
