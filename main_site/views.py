"""Request views for the main JosephlovesJohn site."""

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from josephlovesjohn_site.site_urls import absolute_site_url

from .contact_flow import handle_contact_submission
from .context import build_legal_page_context, build_music_track_context, build_site_context
from .forms import ContactForm
from .site_data import get_music_library_item


def _render_site_section(request, active_section, *, contact_form=None):
    """Render the one-page site shell with the requested active section."""

    return render(
        request,
        "main_site/site.html",
        build_site_context(active_section, contact_form=contact_form, request=request),
    )


def _render_legal_page(request, page_key):
    """Render a legal-information page by key."""

    return render(request, "main_site/legal_page.html", build_legal_page_context(page_key))


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


def music_track(request, slug):
    """Render a dedicated public page for one music track."""
    item = get_music_library_item(slug)
    if item is None:
        raise Http404("Track not found")

    public_slug = str(item.get("public_slug") or item["slug"])
    if slug != public_slug:
        return redirect("main_site:music_track", slug=public_slug, permanent=True)

    return render(request, "main_site/music_track.html", build_music_track_context(request, item))


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
        result = handle_contact_submission(request, form)
        if result.should_redirect:
            return redirect("main_site:contact")

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
