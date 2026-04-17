"""Views and content helpers for the main JosephlovesJohn site."""

import mimetypes
from pathlib import Path
from typing import TypedDict, cast

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import OperationalError, ProgrammingError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from josephlovesjohn_site.assets import resolve_public_asset_source
from josephlovesjohn_site.rate_limits import is_rate_limited
from josephlovesjohn_site.site_urls import absolute_site_url
from shop.models import Product

from .forms import ContactForm
from .models import AlbumArt, AnimationAsset, GigPhoto, HeaderSocialLink, PrimaryNavItem


class HeaderSocialLinkItem(TypedDict):
    """Typed representation of a rendered header social link."""

    href: str
    icon_class: str
    label: str

LEGAL_PAGE_CONTENT = {
    "privacy": {
        "title": "Privacy Policy",
        "eyebrow": "Privacy",
        "subtitle": "How JosephlovesJohn handles account, order, and payment-related information on this site.",
        "sections": [
            {
                "heading": "Who this policy covers",
                "paragraphs": [
                    "This website sells digital music downloads directly to listeners and also lets "
                    "visitors contact us or create an optional customer account.",
                    "The policy covers personal information collected through the website, shop "
                    "account area, checkout flow, and contact forms.",
                ],
            },
            {
                "heading": "Information we collect",
                "bullets": [
                    "Account details such as username, name, and email address.",
                    "Order records such as purchased tracks, totals, timestamps, and download entitlements.",
                    "Payment-related references such as Stripe Checkout Session IDs and Payment Intent IDs.",
                    "Messages you send through the contact form or support requests.",
                    "Technical data needed to keep the site secure and remember cart, login, and cookie preferences.",
                ],
            },
            {
                "heading": "How we use it",
                "bullets": [
                    "To create and manage customer accounts.",
                    "To process orders, verify payment, and provide download access.",
                    "To answer enquiries and support requests.",
                    "To maintain site security, prevent misuse, and keep records required for "
                    "accounting or legal obligations.",
                    "To send marketing only where you have actively opted in.",
                ],
            },
            {
                "heading": "Payments and third parties",
                "paragraphs": [
                    "Payments are processed through Stripe on Stripe-hosted checkout pages. This "
                    "website does not store full card details.",
                    "We share only the information needed to create, verify, and record a payment, "
                    "including your order reference, email address where available, and the items "
                    "being purchased.",
                ],
            },
            {
                "heading": "Retention and your choices",
                "paragraphs": [
                    "We keep order and account information for as long as needed to provide "
                    "downloads, maintain business records, and meet legal or tax obligations.",
                    "You can contact us to request access, correction, or deletion of personal "
                    "information, subject to any records we must keep by law.",
                ],
            },
        ],
    },
    "cookies": {
        "title": "Cookies Policy",
        "eyebrow": "Cookies",
        "subtitle": "How this site uses essential cookies and optional third-party embeds.",
        "sections": [
            {
                "heading": "Essential cookies",
                "paragraphs": [
                    "This site uses essential cookies and similar storage to keep the shop working. "
                    "That includes remembering your cart, maintaining login sessions, protecting "
                    "forms with CSRF tokens, and saving your cookie preference.",
                    "These cookies are needed for services you have asked for, so they load automatically.",
                ],
            },
            {
                "heading": "Optional cookies and embedded services",
                "paragraphs": [
                    "The mailing-list signup embed uses a third-party service. Optional cookies are "
                    "blocked until you allow them.",
                    "You can still use the direct signup link without enabling optional cookies on this site.",
                ],
            },
            {
                "heading": "Stripe and payment pages",
                "paragraphs": [
                    "When you continue to Stripe Checkout, you move to Stripe-hosted pages. Stripe "
                    "may use its own cookies and privacy controls under its own policies.",
                ],
            },
            {
                "heading": "Managing cookies",
                "paragraphs": [
                    "Use the cookie controls on this site to accept optional cookies or keep essential-only mode.",
                    "You can also clear cookies in your browser settings, though doing so may remove "
                    "your cart, login session, and saved site preferences.",
                ],
            },
        ],
    },
    "terms": {
        "title": "Terms of Sale",
        "eyebrow": "Terms",
        "subtitle": "The basic terms that apply when you buy digital music downloads from this website.",
        "sections": [
            {
                "heading": "What you are buying",
                "paragraphs": [
                    "Products sold through this shop are digital music downloads. No physical goods are shipped.",
                    "Prices are shown in GBP. Shipping does not apply to digital downloads.",
                ],
            },
            {
                "heading": "Checkout and payment",
                "paragraphs": [
                    "Orders are placed through Stripe-hosted checkout pages. Payment must be "
                    "confirmed before download access is unlocked.",
                    "Where VAT becomes applicable, checkout and order records should reflect the "
                    "price charged and any required tax treatment.",
                    "The mailing-list signup form is treated as an essential embedded service when "
                    "you choose to use it, because the provider needs cookies or similar storage to "
                    "render and submit the form correctly.",
                ],
            },
            {
                "heading": "Accounts and download access",
                "paragraphs": [
                    "You can buy as a guest or create an account. Logged-in customers can review "
                    "previous confirmed purchases in their account area.",
                    "Download access is provided after payment confirmation and may be limited if "
                    "misuse, fraud, or abuse is detected.",
                ],
            },
            {
                "heading": "Contact and support",
                "paragraphs": [
                    "If you have trouble receiving or using a download, contact us and we will "
                    "investigate and help put it right.",
                ],
            },
        ],
    },
    "refunds": {
        "title": "Refunds and Digital Downloads",
        "eyebrow": "",
        "subtitle": "Important information about cancellation rights and support for digital music downloads.",
        "sections": [
            {
                "heading": "Immediate digital supply",
                "paragraphs": [
                    "By continuing to payment for a digital download, you confirm that supply should "
                    "begin immediately after payment is confirmed.",
                    "Once immediate supply begins, the usual 14-day cancellation right for distance "
                    "sales no longer applies to that digital content.",
                ],
            },
            {
                "heading": "When to contact us",
                "bullets": [
                    "A file does not download after payment confirmation.",
                    "A download is corrupted or materially not as described.",
                    "You were charged more than expected or experienced a duplicate payment.",
                ],
            },
            {
                "heading": "How we handle issues",
                "paragraphs": [
                    "Where there is a genuine delivery, quality, or billing problem, we will review "
                    "the order and aim to provide a replacement download, correction, or refund where "
                    "appropriate.",
                ],
            },
        ],
    },
}

LEGAL_PAGE_ORDER = ("privacy", "cookies", "terms", "refunds")

SPOTIFY_SOCIAL_LINK: HeaderSocialLinkItem = {
    "href": "https://open.spotify.com/artist/27YZiLsfuwfBI5e4BZyTIi?si=rcYZFzPzSPCfartpPGM6gg",
    "icon_class": "icon brands fa-spotify",
    "label": "Spotify",
}


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


def _resolve_asset_source(static_path="", uploaded_file=None):
    """Resolve a gallery asset to a URL, preferring uploaded files."""
    if uploaded_file and _uploaded_file_exists(uploaded_file):
        return {
            "path": uploaded_file.name,
            "url": uploaded_file.url,
            "is_static": False,
        }

    return resolve_public_asset_source(static_path, file_exists=_static_file_exists)


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


def _get_header_social_links() -> list[HeaderSocialLinkItem]:
    """Return active header social links in display order."""
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
                "buy_path": reverse("shop:cart_add", kwargs={"slug": product.slug}),
            }
        )
    return items


def _site_context(active_section, *, contact_form=None):
    """Build the shared rendering context for the one-page site.

    :param active_section: Hash-compatible section slug to activate on load.
    :type active_section: str
    :param contact_form: Optional pre-bound contact form instance.
    :type contact_form: main_site.forms.ContactForm | None
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
        "contact_form": contact_form or ContactForm(),
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
    }


def _render_site_section(request, active_section, *, contact_form=None):
    """Render the one-page site shell with the requested active section."""

    return render(request, "main_site/site.html", _site_context(active_section, contact_form=contact_form))


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
