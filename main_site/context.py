"""Context builders for the main JosephlovesJohn site views."""

from typing import cast

from django.conf import settings
from django.contrib.messages import get_messages
from django.urls import reverse
from josephlovesjohn_site.site_urls import absolute_site_url
from shop.ownership import get_owned_product_slugs

from .content import LEGAL_PAGE_CONTENT
from .forms import ContactForm
from .seo import build_legal_page_seo, build_music_track_seo, build_site_seo
from .site_data import (
    get_album_art_items,
    get_gig_photo_items,
    get_header_social_links,
    get_music_library_items,
    get_primary_nav_items,
)

CANONICAL_ROUTES = {
    "main": "main_site:main",
    "intro": "main_site:intro",
    "music": "main_site:music",
    "art": "main_site:art",
    "contact": "main_site:contact",
}


def build_site_context(active_section, *, contact_form=None, request=None):
    """Build the shared rendering context for the one-page site."""
    section_key = active_section or "main"
    header_social_links = get_header_social_links()
    music_items = get_music_library_items()
    contact_messages = [
        message
        for message in (get_messages(request) if request is not None else [])
        if "contact" in message.extra_tags.split()
    ]
    owned_slug_candidates = [item.get("slug") for item in music_items if item.get("slug")]
    owned_music_slugs = sorted(
        get_owned_product_slugs(getattr(request, "user", None), slugs=owned_slug_candidates)
    )
    return {
        "active_section": active_section,
        "header_social_links": header_social_links,
        "primary_nav_items": get_primary_nav_items(),
        "music_items": music_items,
        "owned_music_slugs": owned_music_slugs,
        "gig_photo_items": get_gig_photo_items(),
        "album_art_items": get_album_art_items(),
        "contact_form": contact_form or ContactForm(),
        "contact_messages": contact_messages,
        "seo": build_site_seo(
            section_key,
            canonical_url=absolute_site_url(reverse(CANONICAL_ROUTES[section_key])),
            header_social_links=cast(list[dict[str, str]], header_social_links),
            music_items=music_items,
        ),
    }


def build_legal_page_context(page_key):
    """Build the rendering context for a legal-information page."""
    page = LEGAL_PAGE_CONTENT[page_key]
    business_name = settings.LEGAL_BUSINESS_NAME
    contact_email = settings.BUSINESS_CONTACT_EMAIL
    postal_address = settings.BUSINESS_POSTAL_ADDRESS
    vat_number = settings.VAT_NUMBER
    contact_lines = [business_name, contact_email]
    if postal_address:
        contact_lines.extend(line.strip() for line in postal_address.splitlines() if line.strip())
    if vat_number:
        contact_lines.append(f"VAT number: {vat_number}")

    return {
        "page": page,
        "contact_lines": contact_lines,
        "business_name": business_name,
        "primary_nav_items": get_primary_nav_items(),
        "seo": build_legal_page_seo(
            page_key,
            page_title=str(page["title"]),
            canonical_url=absolute_site_url(reverse(f"main_site:{page_key}")),
        ),
    }


def build_music_track_context(request, item):
    """Build the rendering context for a dedicated music track page."""
    public_slug = str(item.get("public_slug") or item["slug"])
    canonical_url = absolute_site_url(reverse("main_site:music_track", kwargs={"slug": public_slug}), request)
    return {
        "active_section": "music",
        "item": item,
        "seo": build_music_track_seo(item, canonical_url=canonical_url),
    }
