"""Template context processors for the shop app."""

from .cart import build_cart_summary


def cart_summary(request):
    """Expose the current cart summary to all templates.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: Mapping with the current cart summary.
    :rtype: dict[str, object]
    """
    return {"cart_summary": build_cart_summary(request)}
