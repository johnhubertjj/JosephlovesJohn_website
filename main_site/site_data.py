"""Reusable data builders for the main-site views."""

import mimetypes
from pathlib import Path
from typing import cast

from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.urls import reverse
from josephlovesjohn_site.assets import normalize_asset_path, public_asset_url, resolve_public_asset_source
from shop.models import Product

from .cache import cache_shared_content
from .content import SPOTIFY_SOCIAL_LINK, HeaderSocialLinkItem
from .models import AlbumArt, AnimationAsset, GigPhoto, HeaderSocialLink, PrimaryNavItem

MUSIC_STREAMING_LINKS = {
    "dark-and-light-artist-version": [
        {
            "label": "Spotify",
            "href": "https://open.spotify.com/track/3oUvoKqq4qrlSP5VkCqhvh?si=c0ea820a417d4845",
            "icon_class": "icon brands fa-spotify",
            "action": "Play",
        },
        {
            "label": "iTunes",
            "href": "http://itunes.apple.com/album/id1870775878?ls=1&app=itunes",
            "icon_class": "icon brands fa-itunes-note",
            "action": "Buy",
        },
        {
            "label": "Apple Music",
            "href": "https://music.apple.com/us/song/dark-and-light/1870775884",
            "icon_class": "icon brands fa-apple",
            "action": "Play",
        },
        {
            "label": "Bandcamp",
            "href": "https://josephlovesjohn.bandcamp.com/track/dark-and-light",
            "icon_class": "icon brands fa-bandcamp",
            "action": "Play",
        },
        {
            "label": "YouTube",
            "href": "https://youtu.be/FQHSHiUG_gU?si=r2wMfmQy1e7b86oh",
            "icon_class": "icon brands fa-youtube",
            "action": "Play",
        },
        {
            "label": "Amazon Music",
            "href": "https://music.amazon.co.uk/albums/B0GHXN25VG?marketplaceId=A1F83G8C2ARO7P&musicTerritory=GB&ref=dm_sh_yoh0Fbd0gQDddAFmgQemh3OPO&trackAsin=B0GHXQCHZ9",
            "icon_class": "icon brands fa-amazon",
            "action": "Play",
        },
        {
            "label": "Deezer",
            "href": "https://link.deezer.com/s/339jOD96TC9KXp5iQM3d1",
            "icon_class": "icon fas fa-music",
            "action": "Play",
        },
        {
            "label": "TIDAL",
            "href": "https://tidal.com/track/491362438/u",
            "icon_class": "icon fas fa-water",
            "action": "Play",
        },
    ],
    "dark-and-light-instrumental": [
        {
            "label": "Spotify",
            "href": "https://open.spotify.com/track/3oUvoKqq4qrlSP5VkCqhvh?si=889a04bcb1bf42b7",
            "icon_class": "icon brands fa-spotify",
            "action": "Play",
        },
        {
            "label": "iTunes",
            "href": "http://itunes.apple.com/album/id1882279580?ls=1&app=itunes",
            "icon_class": "icon brands fa-itunes-note",
            "action": "Buy",
        },
        {
            "label": "Apple Music",
            "href": "http://itunes.apple.com/album/id/1882279580",
            "icon_class": "icon brands fa-apple",
            "action": "Play",
        },
        {
            "label": "Bandcamp",
            "href": "https://josephlovesjohn.bandcamp.com",
            "icon_class": "icon brands fa-bandcamp",
            "action": "Play",
        },
        {
            "label": "YouTube",
            "href": "https://youtu.be/KedziCK2Ct0?si=42uMnyZpIANmINH-",
            "icon_class": "icon brands fa-youtube",
            "action": "Play",
        },
        {
            "label": "Amazon Music",
            "href": "https://music.amazon.co.uk/albums/B0GR12KXQN?marketplaceId=A1F83G8C2ARO7P&musicTerritory=GB&ref=dm_sh_BEyLRZz4AMtLG6vjGTnyufJ2J&trackAsin=B0GQZM5P5P",
            "icon_class": "icon brands fa-amazon",
            "action": "Play",
        },
        {
            "label": "Deezer",
            "href": "https://link.deezer.com/s/339jNY0PN3084QcnTPMfA",
            "icon_class": "icon fas fa-music",
            "action": "Play",
        },
        {
            "label": "TIDAL",
            "href": "https://tidal.com/track/503829268/u",
            "icon_class": "icon fas fa-water",
            "action": "Play",
        },
    ],
}

MUSIC_LIBRARY_CACHE_KEY = "music-library-items-v2"

MUSIC_TRACK_PUBLIC_SLUGS = {
    "dark-and-light-artist-version": "dark-and-light",
}

MUSIC_TRACK_SLUG_ALIASES = {
    "original": "dark-and-light-artist-version",
    "dark-and-light": "dark-and-light-artist-version",
    "instrumental": "dark-and-light-instrumental",
}


def _static_file_exists(relative_path):
    """Check whether a static asset exists on disk.

    :param relative_path: Path relative to the ``static`` directory.
    :type relative_path: str
    :returns: ``True`` when the file exists, otherwise ``False``.
    :rtype: bool
    """
    return (Path(settings.BASE_DIR) / "static" / relative_path).is_file()


def _static_file_size(relative_path):
    """Return a static asset size in bytes when the file exists."""
    static_path = Path(settings.BASE_DIR) / "static" / relative_path
    if not static_path.is_file():
        return None

    return static_path.stat().st_size


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


def _resolve_asset_source(static_path="", uploaded_file=None):
    """Resolve a gallery asset to a URL, preferring uploaded files."""
    if uploaded_file and _uploaded_file_exists(uploaded_file):
        return {
            "path": uploaded_file.name,
            "url": uploaded_file.url,
            "is_static": False,
        }

    return resolve_public_asset_source(static_path, file_exists=_static_file_exists)


def _resolve_static_webp_variant(asset):
    """Return a sibling WebP asset for a static source when one exists."""
    if not asset or not asset.get("is_static"):
        return None

    normalized_path = normalize_asset_path(cast(str, asset.get("path") or ""))
    if not normalized_path:
        return None

    if normalized_path.lower().endswith(".webp"):
        return {
            "path": normalized_path,
            "url": public_asset_url(normalized_path),
        }

    webp_path = str(Path(normalized_path).with_suffix(".webp"))
    if not settings.PUBLIC_ASSET_BASE_URL and not _static_file_exists(webp_path):
        return None

    return {
        "path": webp_path,
        "url": public_asset_url(webp_path),
    }


def _resolve_smaller_static_video_variant(asset):
    """Return a smaller sibling MP4 for a static GIF source when available."""
    if not asset or not asset.get("is_static"):
        return None

    normalized_path = normalize_asset_path(cast(str, asset.get("path") or ""))
    if not normalized_path or not normalized_path.lower().endswith(".gif"):
        return None

    mp4_path = str(Path(normalized_path).with_suffix(".mp4"))
    if settings.PUBLIC_ASSET_BASE_URL:
        return {
            "path": mp4_path,
            "url": public_asset_url(mp4_path),
        }

    source_size = _static_file_size(normalized_path)
    if source_size is None:
        return None

    mp4_size = _static_file_size(mp4_path)
    if mp4_size is None or mp4_size >= source_size:
        return None

    return {
        "path": mp4_path,
        "url": public_asset_url(mp4_path),
        "size": mp4_size,
    }


def _build_gig_photo_item(title, image_path="", image_file=None, thumbnail_path="", thumbnail_file=None, alt_text=""):
    """Build a gallery item dictionary when the referenced files exist."""
    image_asset = _resolve_asset_source(static_path=image_path, uploaded_file=image_file)
    if not image_asset:
        return None

    thumbnail_asset = _resolve_asset_source(static_path=thumbnail_path, uploaded_file=thumbnail_file) or image_asset
    item = {
        "title": title,
        "image_path": image_asset["path"],
        "thumbnail_path": thumbnail_asset["path"],
        "image_url": image_asset["url"],
        "thumbnail_url": thumbnail_asset["url"],
        "alt_text": alt_text or title,
    }
    thumbnail_webp_asset = _resolve_static_webp_variant(thumbnail_asset)
    if thumbnail_webp_asset:
        item["thumbnail_webp_path"] = thumbnail_webp_asset["path"]
        item["thumbnail_webp_url"] = thumbnail_webp_asset["url"]
    return item


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
    if kind == "image":
        smaller_video_asset = _resolve_smaller_static_video_variant(asset)
        if smaller_video_asset:
            item["kind"] = "video"
            item["path"] = smaller_video_asset["path"]
            item["url"] = smaller_video_asset["url"]
            item["mime_type"] = mimetypes.guess_type(smaller_video_asset["path"])[0] or "video/mp4"
            item["poster"] = ""
            item["poster_url"] = ""
            item["autoplay"] = True
            item["loop"] = True
            item["muted"] = True
            item["show_controls"] = False
            return item

        item["thumbnail_url"] = asset["url"]
        thumbnail_webp_asset = _resolve_static_webp_variant(asset)
        if thumbnail_webp_asset:
            item["thumbnail_webp_path"] = thumbnail_webp_asset["path"]
            item["thumbnail_webp_url"] = thumbnail_webp_asset["url"]
    if kind == "video":
        item["mime_type"] = mimetypes.guess_type(asset["path"])[0] or "video/mp4"
        poster = _resolve_asset_source(static_path=poster_path, uploaded_file=poster_file)
        item["poster"] = poster["path"] if poster else ""
        item["poster_url"] = poster["url"] if poster else ""
        item["show_controls"] = True
    return item


def _get_header_social_links() -> list[HeaderSocialLinkItem]:
    """Return active header social links in display order."""
    def _build() -> list[HeaderSocialLinkItem]:
        try:
            links = cast(
                list[HeaderSocialLinkItem],
                list(
                    HeaderSocialLink.objects.filter(is_active=True)
                    .order_by("sort_order", "id")
                    .values("href", "icon_class", "label")
                ),
            )
        except (OperationalError, ProgrammingError):
            return []

        spotify_link: HeaderSocialLinkItem | None = None
        ordered_links: list[HeaderSocialLinkItem] = []
        bandcamp_index = None

        for link in links:
            label = (link.get("label") or "").strip().lower()
            icon_class = (link.get("icon_class") or "").lower()

            if label == "spotify" or "fa-spotify" in icon_class:
                spotify_link = SPOTIFY_SOCIAL_LINK.copy()
                continue

            ordered_links.append(link)
            if label == "bandcamp":
                bandcamp_index = len(ordered_links) - 1

        if spotify_link is None:
            spotify_link = SPOTIFY_SOCIAL_LINK.copy()

        insert_at = bandcamp_index + 1 if bandcamp_index is not None else min(1, len(ordered_links))
        ordered_links.insert(insert_at, spotify_link)
        return ordered_links

    return cache_shared_content("header-social-links", _build, cache_empty=False)


def _get_primary_nav_items():
    """Return active primary nav items in display order."""
    def _build():
        try:
            return list(
                PrimaryNavItem.objects.filter(is_active=True)
                .order_by("sort_order", "id")
                .values("href", "label")
            )
        except (OperationalError, ProgrammingError):
            return []

    return cache_shared_content("primary-nav-items", _build, cache_empty=False)


def _get_gig_photo_items():
    """Return active gig photo items for the art gallery.

    The function prefers admin-managed database records and falls back to the
    bundled static manifest when the database is unavailable or empty.

    :returns: A list of normalized gig photo dictionaries.
    :rtype: list[dict[str, str]]
    """
    def _build():
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

    return cache_shared_content("gig-photo-items", _build, cache_empty=False)


def _get_album_art_items():
    """Return album art entries whose backing static assets still exist.

    :returns: A list of album art dictionaries ready for template rendering.
    :rtype: list[dict[str, object]]
    """
    def _build():
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

        for animation in configured_animations:
            item = _build_album_art_item(
                kind=animation.media_kind,
                title=animation.title,
                asset_path=animation.file_path,
                asset_file=animation.file_upload,
                alt_text=animation.alt_text,
                featured=animation.featured,
                fit_contain=animation.fit_contain,
                poster_path=animation.poster_path,
                poster_file=animation.poster_upload,
            )
            if item:
                items.append((animation.sort_order, 1, animation.id, item))

        items.sort(key=lambda row: (row[0], row[1], row[2]))
        return [row[3] for row in items]

    return cache_shared_content("album-art-items", _build, cache_empty=False)


def _get_music_library_items():
    """Return music library items with a precomputed share route.

    :returns: Music library dictionaries enriched for template rendering.
    :rtype: list[dict[str, object]]
    """
    def _build():
        share_path = reverse("main_site:music")
        try:
            products = list(Product.objects.filter(is_published=True).order_by("sort_order", "id"))
        except (OperationalError, ProgrammingError):
            return []

        items = []
        for product in products:
            public_slug = MUSIC_TRACK_PUBLIC_SLUGS.get(product.slug, product.slug)
            track_path = reverse("main_site:music_track", kwargs={"slug": public_slug})
            items.append(
                {
                    "slug": product.slug,
                    "public_slug": public_slug,
                    "title": product.title,
                    "artist_name": product.artist_name,
                    "meta": product.meta,
                    "description": product.description,
                    "art_path": product.art_path,
                    "art_url": product.art_url,
                    "art_alt": product.art_alt or product.title,
                    "player_id": product.player_id,
                    "file_wav": product.preview_file_wav,
                    "file_wav_url": product.preview_wav_url,
                    "file_mp3": product.preview_file_mp3,
                    "file_mp3_url": product.preview_mp3_url,
                    "price": f"{product.price:.2f}",
                    "price_display": product.price_display,
                    "is_reversed": product.is_reversed,
                    "share_path": share_path,
                    "track_path": track_path,
                    "streaming_links": MUSIC_STREAMING_LINKS.get(product.slug, []),
                    "buy_path": reverse("shop:cart_add", kwargs={"slug": product.slug}),
                }
            )
        return items

    return cache_shared_content(MUSIC_LIBRARY_CACHE_KEY, _build, cache_empty=False)


def _get_music_library_item(slug):
    """Return one published music library item by slug."""
    resolved_slug = MUSIC_TRACK_SLUG_ALIASES.get(slug, slug)
    return next(
        (
            item
            for item in _get_music_library_items()
            if item.get("slug") == resolved_slug or item.get("public_slug") == resolved_slug
        ),
        None,
    )
