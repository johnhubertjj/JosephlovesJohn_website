"""Views for the mastering services site."""

from django.shortcuts import render


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
        {"entered_from_home": request.GET.get("from_home") == "1"},
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
        {"subfolder": subfolder},
    )
