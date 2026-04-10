from pathlib import Path

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.shortcuts import render

from .models import GigPhoto


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
    return (Path(settings.BASE_DIR) / "static" / relative_path).is_file()


def _normalize_static_path(path):
    normalized = (path or "").strip()
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")
    if normalized.startswith("static/"):
        normalized = normalized[7:]
    return normalized


def _build_gig_photo_item(title, image_path, thumbnail_path="", alt_text=""):
    image_relative = _normalize_static_path(image_path)
    thumbnail_relative = _normalize_static_path(thumbnail_path) if thumbnail_path else image_relative
    if not image_relative or not _static_file_exists(image_relative):
        return None
    if not thumbnail_relative or not _static_file_exists(thumbnail_relative):
        thumbnail_relative = image_relative
    return {
        "title": title,
        "image_path": image_relative,
        "thumbnail_path": thumbnail_relative,
        "alt_text": alt_text or title,
    }


def _get_gig_photo_items():
    try:
        configured_gig_photos = list(GigPhoto.objects.filter(is_active=True).order_by("sort_order", "id"))
    except (OperationalError, ProgrammingError):
        configured_gig_photos = []

    items = []
    for photo in configured_gig_photos:
        item = _build_gig_photo_item(
            title=photo.title,
            image_path=photo.image_path,
            thumbnail_path=photo.thumbnail_path,
            alt_text=photo.alt_text,
        )
        if item:
            items.append(item)

    if items:
        return items

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
    items = []
    for asset in ALBUM_ART_MANIFEST:
        if not _static_file_exists(asset["path"]):
            continue

        item = asset.copy()
        if item["kind"] == "video":
            item["mime_type"] = "video/mp4"
            poster = item.get("poster")
            if poster and not _static_file_exists(poster):
                item["poster"] = ""

        items.append(item)
    return items


def _site_context(active_section):
    return {
        "active_section": active_section,
        "gig_photo_items": _get_gig_photo_items(),
        "album_art_items": _get_album_art_items(),
    }


def main(request):
    return render(request, "main_site/site.html", _site_context(""))


def intro(request):
    return render(request, "main_site/site.html", _site_context("intro"))


def music(request):
    return render(request, "main_site/site.html", _site_context("music"))


def art(request):
    return render(request, "main_site/site.html", _site_context("art"))


def contact(request):
    return render(request, "main_site/site.html", _site_context("contact"))
