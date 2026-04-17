"""Views for the mastering services site."""

from django.shortcuts import render
from josephlovesjohn_site.assets import public_asset_url
from josephlovesjohn_site.site_urls import absolute_site_url


def home(request):
    """Render the mastering services landing page.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the mastering home page.
    :rtype: django.http.HttpResponse
    """
    return render(
        request,
        "mastering/home.html",
        {
            "entered_from_home": request.GET.get("from_home") == "1",
            "seo": {
                "title": "Mastering Services | JosephlovesJohn",
                "description": (
                    "Independent, taste-first mastering services from JosephlovesJohn, focused on depth, clarity, "
                    "and emotional translation."
                ),
                "canonical_url": absolute_site_url(request.path),
                "image_url": absolute_site_url(public_asset_url("images/jlovesj_symbol-my_version3.png")),
                "robots": "index,follow",
            },
        },
    )


def subfolder(request, subfolder):
    """Render a placeholder page for a mastering subfolder.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :param subfolder: The requested mastering subsection slug.
    :type subfolder: str
    :returns: A rendered response for the requested placeholder page.
    :rtype: django.http.HttpResponse
    """
    return render(
        request,
        "mastering/subfolder.html",
        {
            "subfolder": subfolder,
            "seo": {
                "title": f"{subfolder.replace('-', ' ').title()} | Mastering Services | JosephlovesJohn",
                "description": "Reserved placeholder page for a future JosephlovesJohn mastering services subsection.",
                "canonical_url": absolute_site_url(request.path),
                "image_url": absolute_site_url(public_asset_url("images/jlovesj_symbol-my_version3.png")),
                "robots": "noindex,follow",
            },
        },
    )
