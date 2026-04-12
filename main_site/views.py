"""Views and content helpers for the main JosephlovesJohn site."""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.shortcuts import render
from django.templatetags.static import static as static_url
from django.urls import reverse
from shop.models import Product

from .models import AlbumArt, AnimationAsset, GigPhoto, HeaderSocialLink, PrimaryNavItem


def _static_file_exists(relative_path):
    """Check whether a static asset exists on disk.

    :param relative_path: Path relative to the ``static`` directory.
    :type relative_path: str
    :returns: ``True`` when the file exists, otherwise ``False``.
    :rtype: bool
    """
    return (Path(settings.BASE_DIR) / "static" / relative_path).is_file()


def _uploaded_file_exists(file_field):
    """Check whether an uploaded media file exists in storage."""
    if not file_field:
        return False

    file_name = getattr(file_field, "name", "")
    if not file_name:
        return False

    try:
        return file_field.storage.exists(file_name)
    except OSError:
        return False


def _normalize_static_path(path):
    """Normalize a static asset path for lookups and template usage.

    :param path: Raw file path value that may include leading slashes or a
        ``static/`` prefix.
    :type path: str | None
    :returns: A normalized path relative to ``static/``.
    :rtype: str
    """
    normalized = (path or "").strip()
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")
    if normalized.startswith("static/"):
        normalized = normalized[7:]
    return normalized


def _resolve_asset_source(static_path="", uploaded_file=None):
    """Resolve a gallery asset to a URL, preferring uploaded files."""
    if uploaded_file and _uploaded_file_exists(uploaded_file):
        return {
            "path": uploaded_file.name,
            "url": uploaded_file.url,
            "is_static": False,
        }

    relative_path = _normalize_static_path(static_path)
    if relative_path and _static_file_exists(relative_path):
        return {
            "path": relative_path,
            "url": static_url(relative_path),
            "is_static": True,
        }

    return None


def _build_gig_photo_item(title, image_path="", image_file=None, thumbnail_path="", thumbnail_file=None, alt_text=""):
    """Build a gallery item dictionary when the referenced files exist."""
    image_asset = _resolve_asset_source(static_path=image_path, uploaded_file=image_file)
    if not image_asset:
        return None

    thumbnail_asset = _resolve_asset_source(static_path=thumbnail_path, uploaded_file=thumbnail_file) or image_asset
    return {
        "title": title,
        "image_path": image_asset["path"],
        "thumbnail_path": thumbnail_asset["path"],
        "image_url": image_asset["url"],
        "thumbnail_url": thumbnail_asset["url"],
        "alt_text": alt_text or title,
    }


def _build_album_art_item(
    *,
    kind,
    title,
    asset_path="",
    asset_file=None,
    alt_text="",
    featured=False,
    fit_contain=False,
    poster_path="",
    poster_file=None,
):
    """Build an album art or animation item when the referenced files exist."""
    asset = _resolve_asset_source(static_path=asset_path, uploaded_file=asset_file)
    if not asset:
        return None

    item = {
        "kind": kind,
        "path": asset["path"],
        "url": asset["url"],
        "caption": title,
        "alt": alt_text or title,
        "featured": featured,
        "fit_contain": fit_contain,
    }
    if kind == "video":
        item["mime_type"] = mimetypes.guess_type(asset["path"])[0] or "video/mp4"
        poster = _resolve_asset_source(static_path=poster_path, uploaded_file=poster_file)
        item["poster"] = poster["path"] if poster else ""
        item["poster_url"] = poster["url"] if poster else ""
    return item


def _get_header_social_links():
    """Return active header social links in display order."""
    try:
        return list(
            HeaderSocialLink.objects.filter(is_active=True)
            .order_by("sort_order", "id")
            .values("href", "icon_class", "label")
        )
    except (OperationalError, ProgrammingError):
        return []


def _get_primary_nav_items():
    """Return active primary nav items in display order."""
    try:
        return list(
            PrimaryNavItem.objects.filter(is_active=True)
            .order_by("sort_order", "id")
            .values("href", "label")
        )
    except (OperationalError, ProgrammingError):
        return []


def _get_gig_photo_items():
    """Return active gig photo items for the art gallery.

    The function prefers admin-managed database records and falls back to the
    bundled static manifest when the database is unavailable or empty.

    :returns: A list of normalized gig photo dictionaries.
    :rtype: list[dict[str, str]]
    """
    try:
        configured_gig_photos = list(GigPhoto.objects.filter(is_active=True).order_by("sort_order", "id"))
    except (OperationalError, ProgrammingError):
        return []

    items = []
    for photo in configured_gig_photos:
        item = _build_gig_photo_item(
            title=photo.title,
            image_path=photo.image_path,
            image_file=photo.image_file,
            thumbnail_path=photo.thumbnail_path,
            thumbnail_file=photo.thumbnail_file,
            alt_text=photo.alt_text,
        )
        if item:
            items.append(item)

    return items


def _get_album_art_items():
    """Return album art entries whose backing static assets still exist.

    :returns: A list of album art dictionaries ready for template rendering.
    :rtype: list[dict[str, object]]
    """
    try:
        configured_album_art = list(AlbumArt.objects.filter(is_active=True).order_by("sort_order", "id"))
        configured_animations = list(AnimationAsset.objects.filter(is_active=True).order_by("sort_order", "id"))
    except (OperationalError, ProgrammingError):
        return []

    items = []
    for asset in configured_album_art:
        item = _build_album_art_item(
            kind="image",
            title=asset.title,
            asset_path=asset.image_path,
            asset_file=asset.image_file,
            alt_text=asset.alt_text,
            featured=asset.featured,
            fit_contain=asset.fit_contain,
        )
        if item:
            items.append((asset.sort_order, 0, asset.id, item))

    for asset in configured_animations:
        item = _build_album_art_item(
            kind=asset.media_kind,
            title=asset.title,
            asset_path=asset.file_path,
            asset_file=asset.file_upload,
            alt_text=asset.alt_text,
            featured=asset.featured,
            fit_contain=asset.fit_contain,
            poster_path=asset.poster_path,
            poster_file=asset.poster_upload,
        )
        if item:
            items.append((asset.sort_order, 1, asset.id, item))

    items.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in items]


def _get_music_library_items():
    """Return music library items with a precomputed share route.

    :returns: Music library dictionaries enriched for template rendering.
    :rtype: list[dict[str, object]]
    """
    share_path = reverse("main_site:music")
    try:
        products = list(Product.objects.filter(is_published=True).order_by("sort_order", "id"))
    except (OperationalError, ProgrammingError):
        return []

    items = []
    for product in products:
        items.append(
            {
                "slug": product.slug,
                "title": product.title,
                "meta": product.meta,
                "art_path": product.art_path,
                "art_alt": product.art_alt or product.title,
                "player_id": product.player_id,
                "file_wav": product.preview_file_wav,
                "file_mp3": product.preview_file_mp3,
                "price_display": product.price_display,
                "is_reversed": product.is_reversed,
                "share_path": share_path,
                "buy_path": reverse("shop:cart_add", kwargs={"slug": product.slug}),
            }
        )
    return items


def _site_context(active_section):
    """Build the shared rendering context for the one-page site.

    :param active_section: Hash-compatible section slug to activate on load.
    :type active_section: str
    :returns: Template context for the main site page.
    :rtype: dict[str, object]
    """
    return {
        "active_section": active_section,
        "header_social_links": _get_header_social_links(),
        "primary_nav_items": _get_primary_nav_items(),
        "music_items": _get_music_library_items(),
        "gig_photo_items": _get_gig_photo_items(),
        "album_art_items": _get_album_art_items(),
    }


def main(request):
    """Render the default one-page site view.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the main landing page.
    :rtype: django.http.HttpResponse
    """
    return render(request, "main_site/site.html", _site_context(""))


def intro(request):
    """Render the one-page site with the intro section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the intro route.
    :rtype: django.http.HttpResponse
    """
    return render(request, "main_site/site.html", _site_context("intro"))


def music(request):
    """Render the one-page site with the music section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the music route.
    :rtype: django.http.HttpResponse
    """
    return render(request, "main_site/site.html", _site_context("music"))


def art(request):
    """Render the one-page site with the art section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the art route.
    :rtype: django.http.HttpResponse
    """
    return render(request, "main_site/site.html", _site_context("art"))


def contact(request):
    """Render the one-page site with the contact section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the contact route.
    :rtype: django.http.HttpResponse
    """
    return render(request, "main_site/site.html", _site_context("contact"))
