"""Views and content helpers for the main JosephlovesJohn site."""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.shortcuts import render
from django.templatetags.static import static as static_url
from django.urls import reverse

from .models import AlbumArt, AnimationAsset, GigPhoto

HEADER_SOCIAL_LINKS = (
    {
        "href": "https://josephlovesjohn.bandcamp.com",
        "icon_class": "icon brands fa-bandcamp",
        "label": "Bandcamp",
    },
    {
        "href": "https://www.instagram.com/josephlovesjohn_music/",
        "icon_class": "icon brands fa-instagram",
        "label": "Instagram",
    },
    {
        "href": "https://www.youtube.com/@JosephlovesJohn",
        "icon_class": "icon brands fa-youtube",
        "label": "YouTube",
    },
    {
        "href": "https://music.amazon.co.uk/artists/B0GHXDGN9M/josephlovesjohn",
        "icon_class": "icon brands fa-amazon",
        "label": "Amazon Music",
    },
    {
        "href": "https://music.apple.com/us/artist/josephlovesjohn/1869723292",
        "icon_class": "icon brands fa-apple",
        "label": "Apple Music",
    },
    {
        "href": "https://www.tiktok.com/@joseph_loves_john",
        "icon_class": "icon brands fa-tiktok",
        "label": "TikTok",
    },
)

PRIMARY_NAV_ITEMS = (
    {"href": "#intro", "label": "Intro"},
    {"href": "#music", "label": "Music"},
    {"href": "#art", "label": "Art"},
    {"href": "#contact", "label": "Contact"},
)

MUSIC_LIBRARY_MANIFEST = (
    {
        "slug": "dark-and-light-artist-version",
        "title": "Dark and Light - Artist Version",
        "meta": "Single",
        "art_path": "images/album_art/dark_and_light_artist_cover.jpg",
        "art_alt": "Dark and Light artist cover artwork",
        "player_id": "dark-and-light-artist-player",
        "file_wav": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.wav",
        "file_mp3": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.mp3",
        "price_display": "£1.00",
        "is_reversed": False,
    },
    {
        "slug": "dark-and-light-instrumental",
        "title": "Dark and Light - Instrumental",
        "meta": "Instrumental Mix",
        "art_path": "images/album_art/dark_and_light_instrumental.jpg",
        "art_alt": "Dark and Light instrumental artwork",
        "player_id": "dark-and-light-instrumental-player",
        "file_wav": "audio/dark_and_light_final_instrumental_v3_24_192.wav",
        "file_mp3": "audio/dark_and_light_final_instrumental_v3_24_192.mp3",
        "price_display": "£1.00",
        "is_reversed": True,
    },
)

ALBUM_ART_MANIFEST = (
    {
        "kind": "image",
        "path": "images/album_art/dark_and_light_artist_cover.jpg",
        "caption": "Dark and Light - Artist Cover",
        "alt": "Dark and Light artist cover artwork",
        "featured": True,
    },
    {
        "kind": "image",
        "path": "images/album_art/dark_and_light_instrumental.jpg",
        "caption": "Dark and Light - Instrumental Artwork",
        "alt": "Dark and Light instrumental artwork",
        "featured": True,
    },
    {
        "kind": "image",
        "path": "images/album_art/Current_artist_profile_picture.jpg",
        "caption": "Current Artist Profile",
        "alt": "Current artist profile portrait",
        "featured": False,
    },
    {
        "kind": "image",
        "path": "images/album_art/symbol_animation.gif",
        "caption": "Symbol Animation",
        "alt": "Symbol animation artwork",
        "featured": False,
    },
    {
        "kind": "image",
        "path": "images/album_art/buddlea_animation.gif",
        "caption": "Buddlea Animation",
        "alt": "Buddlea animation artwork",
        "featured": False,
        "fit_contain": True,
    },
)

BRISTOL_FOLK_HOUSE_GIG_PHOTO_MAP = {
    1: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_1.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_1_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 1",
    },
    2: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_2.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_2_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 2",
    },
    3: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_3.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_3_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 3",
    },
    4: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_4.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_4_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 4",
    },
    5: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_5.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_5_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 5",
    },
    6: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_6.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_6_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 6",
    },
    7: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_7.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_7_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 7",
    },
    8: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_8.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_8_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 8",
    },
    9: {
        "title": "Bristol Folk House 31 03 2026",
        "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_9.jpeg",
        "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_9_thumb.jpg",
        "alt_text": "Bristol Folk House gig photo 9",
    },
}

DEFAULT_GIG_PHOTO_LIBRARY = (
    {
        "title": "Sofa Session",
        "image_path": "images/gig_photos/sofa_photos_1.jpeg",
        "thumbnail_path": "images/gig_photos/sofa_photos_1.jpeg",
        "alt_text": "Gig photo - sofa session 1",
    },
    {
        "title": "Sofa Session",
        "image_path": "images/gig_photos/sofa_photos2.jpeg",
        "thumbnail_path": "images/gig_photos/sofa_photos2.jpeg",
        "alt_text": "Gig photo - sofa session 2",
    },
    {
        "title": "Sofa Session",
        "image_path": "images/gig_photos/sofa_photos3.jpeg",
        "thumbnail_path": "images/gig_photos/sofa_photos3.jpeg",
        "alt_text": "Gig photo - sofa session 3",
    },
    *tuple(BRISTOL_FOLK_HOUSE_GIG_PHOTO_MAP[index] for index in sorted(BRISTOL_FOLK_HOUSE_GIG_PHOTO_MAP)),
)


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
        configured_gig_photos = []
    else:
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

    items = []
    for asset in DEFAULT_GIG_PHOTO_LIBRARY:
        item = _build_gig_photo_item(
            title=asset["title"],
            image_path=asset["image_path"],
            thumbnail_path=asset.get("thumbnail_path", ""),
            alt_text=asset.get("alt_text", ""),
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
        configured_album_art = []
        configured_animations = []
    else:
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

    items = []
    for asset in ALBUM_ART_MANIFEST:
        item = _build_album_art_item(
            kind=asset["kind"],
            title=asset["caption"],
            asset_path=asset["path"],
            alt_text=asset.get("alt", ""),
            featured=asset.get("featured", False),
            fit_contain=asset.get("fit_contain", False),
            poster_path=asset.get("poster", ""),
        )
        if not item:
            continue
        items.append(item)
    return items


def _get_music_library_items():
    """Return music library items with a precomputed share route.

    :returns: Music library dictionaries enriched for template rendering.
    :rtype: list[dict[str, object]]
    """
    share_path = reverse("main_site:music")
    items = []
    for asset in MUSIC_LIBRARY_MANIFEST:
        item = asset.copy()
        item["share_path"] = share_path
        item["buy_path"] = reverse("shop:cart_add", kwargs={"slug": asset["slug"]})
        items.append(item)
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
        "header_social_links": HEADER_SOCIAL_LINKS,
        "primary_nav_items": PRIMARY_NAV_ITEMS,
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
