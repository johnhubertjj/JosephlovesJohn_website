"""Template context processors for the shop app."""

from .cart import build_cart_summary, empty_cart_summary

_CART_TEMPLATE_NAMES = {"main", "intro", "music", "art", "contact"}


def cart_summary(request):
    """Expose the current cart summary to all templates.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: Mapping with the current cart summary.
    :rtype: dict[str, object]
    """
    resolver_match = getattr(request, "resolver_match", None)
    if (
        resolver_match is None
        or resolver_match.namespace != "main_site"
        or resolver_match.url_name not in _CART_TEMPLATE_NAMES
    ):
        return {"cart_summary": empty_cart_summary()}

    return {"cart_summary": build_cart_summary(request, use_cache=True)}
