from pathlib import Path

from django.conf import settings
from django.shortcuts import render


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
    },
)


def _static_file_exists(relative_path):
    return (Path(settings.BASE_DIR) / "static" / relative_path).is_file()


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
