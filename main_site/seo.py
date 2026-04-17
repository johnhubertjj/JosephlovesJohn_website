"""SEO metadata and structured-data helpers for the public site."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

from josephlovesjohn_site.assets import public_asset_url
from josephlovesjohn_site.site_urls import absolute_site_url

SITE_SOCIAL_IMAGE = "images/album_art/Current_artist_profile_picture.jpg"

SITE_SEO = {
    "main": {
        "title": "JosephlovesJohn | Independent Music, Art, and Mastering in Bristol",
        "description": (
            "Discover JosephlovesJohn's music, artwork, live visuals, contact details, and direct download shop "
            "from Bristol-based independent artist JosephlovesJohn."
        ),
        "canonical_route": "main_site:main",
    },
    "intro": {
        "title": "About JosephlovesJohn | Music and Updates",
        "description": (
            "Learn more about JosephlovesJohn, join the mailing list for updates, and explore the artist's "
            "melancholic independent music and creative work."
        ),
        "canonical_route": "main_site:intro",
    },
    "music": {
        "title": "Music | JosephlovesJohn Downloads and Listening",
        "description": (
            "Listen to JosephlovesJohn tracks, preview new releases, and buy direct MP3 and WAV downloads "
            "from the official music page."
        ),
        "canonical_route": "main_site:music",
    },
    "art": {
        "title": "Artwork and Gig Photos | JosephlovesJohn",
        "description": (
            "Browse JosephlovesJohn artwork, animation pieces, and gig photography from live performances "
            "and visual projects."
        ),
        "canonical_route": "main_site:art",
    },
    "contact": {
        "title": "Contact JosephlovesJohn",
        "description": "Get in touch with JosephlovesJohn for music, collaborations, gigs, artwork, or enquiries.",
        "canonical_route": "main_site:contact",
    },
}

LEGAL_PAGE_SEO = {
    "privacy": {
        "description": "Read the JosephlovesJohn privacy policy covering accounts, orders, payments, and enquiries.",
        "canonical_route": "main_site:privacy",
    },
    "cookies": {
        "description": (
            "Read how JosephlovesJohn uses essential cookies, optional embeds, and checkout-related services."
        ),
        "canonical_route": "main_site:cookies",
    },
    "terms": {
        "description": "Review the JosephlovesJohn terms of sale for digital music downloads, payments, and accounts.",
        "canonical_route": "main_site:terms",
    },
    "refunds": {
        "description": "Understand refund and cancellation information for JosephlovesJohn digital music downloads.",
        "canonical_route": "main_site:refunds",
    },
}


def _structured_data_script(payload: Mapping[str, object]) -> str:
    """Serialize one structured-data payload for direct template rendering."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _same_as_links(header_social_links: Sequence[Mapping[str, str]]) -> list[str]:
    """Return canonical external profile links suitable for structured data."""
    hrefs: list[str] = []
    for link in header_social_links:
        href = (link.get("href") or "").strip()
        if href.startswith(("http://", "https://")):
            hrefs.append(href)
    return hrefs


def build_site_seo(
    section_key: str,
    *,
    canonical_url: str,
    header_social_links: Sequence[Mapping[str, str]],
    music_items: list[dict[str, object]],
) -> dict[str, object]:
    """Return SEO metadata plus JSON-LD strings for a public site route."""
    config = SITE_SEO[section_key]
    image_url = absolute_site_url(public_asset_url(SITE_SOCIAL_IMAGE))
    same_as = _same_as_links(header_social_links)
    structured_data: list[dict[str, object]] = [
        {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "JosephlovesJohn",
            "url": canonical_url,
            "image": image_url,
            "jobTitle": "Singer, composer, guitarist, and bassist",
            "description": config["description"],
            "sameAs": same_as,
        }
    ]

    if section_key == "music":
        item_list: list[dict[str, object]] = []
        for index, item in enumerate(music_items, start=1):
            title = str(item.get("title") or "")
            art_url = str(item.get("art_url") or item.get("art_path") or "")
            price = str(item.get("price") or "")
            slug = str(item.get("slug") or "")
            item_url = f"{canonical_url}#{slug}" if slug else canonical_url
            item_list.append(
                {
                    "@type": "ListItem",
                    "position": index,
                    "item": {
                        "@type": "MusicRecording",
                        "name": title,
                        "byArtist": {"@type": "Person", "name": "JosephlovesJohn"},
                        "url": item_url,
                        "image": absolute_site_url(art_url),
                        "offers": {
                            "@type": "Offer",
                            "priceCurrency": "GBP",
                            "price": price,
                            "availability": "https://schema.org/InStock",
                            "url": canonical_url,
                        },
                    },
                }
            )

        structured_data.append(
            {
                "@context": "https://schema.org",
                "@type": "ItemList",
                "name": "JosephlovesJohn music downloads",
                "itemListElement": item_list,
            }
        )

    return {
        "title": config["title"],
        "description": config["description"],
        "canonical_url": canonical_url,
        "image_url": image_url,
        "robots": "index,follow",
        "structured_data": [_structured_data_script(payload) for payload in structured_data],
    }


def build_legal_page_seo(page_key: str, *, page_title: str, canonical_url: str) -> dict[str, object]:
    """Return SEO metadata for one legal page."""
    config = LEGAL_PAGE_SEO[page_key]
    return {
        "title": f"{page_title} | JosephlovesJohn",
        "description": config["description"],
        "canonical_url": canonical_url,
        "image_url": absolute_site_url(public_asset_url(SITE_SOCIAL_IMAGE)),
        "robots": "index,follow",
        "structured_data": [],
    }
