"""Views and content helpers for the main JosephlovesJohn site."""

from typing import cast

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from josephlovesjohn_site.rate_limits import is_rate_limited
from josephlovesjohn_site.site_urls import absolute_site_url
from shop.ownership import get_owned_product_slugs

from . import site_data as _site_data
from .content import LEGAL_PAGE_CONTENT
from .forms import ContactForm
from .seo import build_legal_page_seo, build_site_seo

_static_file_exists = _site_data._static_file_exists
_uploaded_file_exists = _site_data._uploaded_file_exists
_resolve_asset_source = _site_data._resolve_asset_source
_build_gig_photo_item = _site_data._build_gig_photo_item
_build_album_art_item = _site_data._build_album_art_item
_get_header_social_links = _site_data._get_header_social_links
_get_primary_nav_items = _site_data._get_primary_nav_items
_get_gig_photo_items = _site_data._get_gig_photo_items
_get_album_art_items = _site_data._get_album_art_items
_get_music_library_items = _site_data._get_music_library_items

HeaderSocialLink = _site_data.HeaderSocialLink
PrimaryNavItem = _site_data.PrimaryNavItem
GigPhoto = _site_data.GigPhoto
AlbumArt = _site_data.AlbumArt
Product = _site_data.Product

CANONICAL_ROUTES = {
    "main": "main_site:main",
    "intro": "main_site:intro",
    "music": "main_site:music",
    "art": "main_site:art",
    "contact": "main_site:contact",
}


def _site_context(active_section, *, contact_form=None, request=None):
    """Build the shared rendering context for the one-page site.

    :param active_section: Hash-compatible section slug to activate on load.
    :type active_section: str
    :param contact_form: Optional pre-bound contact form instance.
    :type contact_form: main_site.forms.ContactForm | None
    :returns: Template context for the main site page.
    :rtype: dict[str, object]
    """
    section_key = active_section or "main"
    header_social_links = _get_header_social_links()
    music_items = _get_music_library_items()
    owned_slug_candidates = [item.get("slug") for item in music_items if item.get("slug")]
    owned_music_slugs = sorted(
        get_owned_product_slugs(getattr(request, "user", None), slugs=owned_slug_candidates)
    )
    return {
        "active_section": active_section,
        "header_social_links": header_social_links,
        "primary_nav_items": _get_primary_nav_items(),
        "music_items": music_items,
        "owned_music_slugs": owned_music_slugs,
        "gig_photo_items": _get_gig_photo_items(),
        "album_art_items": _get_album_art_items(),
        "contact_form": contact_form or ContactForm(),
        "seo": build_site_seo(
            section_key,
            canonical_url=absolute_site_url(reverse(CANONICAL_ROUTES[section_key])),
            header_social_links=cast(list[dict[str, str]], header_social_links),
            music_items=music_items,
        ),
    }


def _legal_page_context(page_key):
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
        "primary_nav_items": _get_primary_nav_items(),
        "seo": build_legal_page_seo(
            page_key,
            page_title=str(page["title"]),
            canonical_url=absolute_site_url(reverse(f"main_site:{page_key}")),
        ),
    }


def _render_site_section(request, active_section, *, contact_form=None):
    """Render the one-page site shell with the requested active section."""

    return render(
        request,
        "main_site/site.html",
        _site_context(active_section, contact_form=contact_form, request=request),
    )


def _render_legal_page(request, page_key):
    """Render a legal-information page by key."""

    return render(request, "main_site/legal_page.html", _legal_page_context(page_key))


def main(request):
    """Render the default one-page site view.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the main landing page.
    :rtype: django.http.HttpResponse
    """
    return _render_site_section(request, "")


def intro(request):
    """Render the one-page site with the intro section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the intro route.
    :rtype: django.http.HttpResponse
    """
    return _render_site_section(request, "intro")


def music(request):
    """Render the one-page site with the music section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the music route.
    :rtype: django.http.HttpResponse
    """
    return _render_site_section(request, "music")


def art(request):
    """Render the one-page site with the art section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the art route.
    :rtype: django.http.HttpResponse
    """
    return _render_site_section(request, "art")


def contact(request):
    """Render the one-page site with the contact section activated.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the contact route.
    :rtype: django.http.HttpResponse
    """
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            if cleaned.get("website"):
                messages.success(request, "Thanks, your message has been sent.")
                return redirect("main_site:contact")
            if is_rate_limited(
                request,
                scope="contact-form",
                limit=settings.CONTACT_RATE_LIMIT_ATTEMPTS,
                window_seconds=settings.CONTACT_RATE_LIMIT_WINDOW,
                extra_identifier=cleaned["email"],
            ):
                messages.error(
                    request,
                    "Too many messages have been sent from this connection. Please try again later.",
                )
                return _render_site_section(request, "contact", contact_form=form)
            message_body = (
                f"New website contact form submission\n\n"
                f"Name: {cleaned['name']}\n"
                f"Email: {cleaned['email']}\n\n"
                f"Message:\n{cleaned['message']}"
            )
            email_message = EmailMessage(
                subject=f"Website contact from {cleaned['name']}",
                body=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_RECIPIENT_EMAIL],
                reply_to=[cleaned["email"]],
            )
            try:
                email_message.send(fail_silently=False)
            except Exception:  # pragma: no cover - exercised in production mail failures.
                messages.error(
                    request,
                    "Your message could not be sent right now. Please try again in a moment.",
                )
                return _render_site_section(request, "contact", contact_form=form)

            messages.success(request, "Thanks, your message has been sent.")
            return redirect("main_site:contact")

        messages.error(request, "Please correct the highlighted fields and try again.")
        return _render_site_section(request, "contact", contact_form=form)

    return _render_site_section(request, "contact")


def privacy(request):
    """Render the privacy policy page."""

    return _render_legal_page(request, "privacy")


def cookies(request):
    """Render the cookies policy page."""

    return _render_legal_page(request, "cookies")


def terms(request):
    """Render the shop terms page."""

    return _render_legal_page(request, "terms")


def refunds(request):
    """Render the refunds and digital downloads page."""

    return _render_legal_page(request, "refunds")


def robots_txt(request):
    """Return a simple robots policy and sitemap hint for search crawlers."""
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {absolute_site_url(reverse('sitemap'), request)}",
            "",
        ]
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")
