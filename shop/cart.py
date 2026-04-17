"""Session-backed cart helpers for the demo music shop."""

from decimal import Decimal

from django.urls import reverse

from .models import Product
from .ownership import get_owned_product_slugs

CART_SESSION_KEY = "shop_cart"


def _get_cart_store(request):
    """Return the mutable cart payload stored in the session.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: Session cart payload.
    :rtype: list[str]
    """
    cart = request.session.get(CART_SESSION_KEY)
    if isinstance(cart, list):
        return cart
    return []


def get_cart_slugs(request):
    """Return the ordered product slugs stored in the cart.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: Ordered cart slugs.
    :rtype: list[str]
    """
    return list(_get_cart_store(request))


def save_cart_slugs(request, slugs):
    """Persist the supplied slugs to the session cart.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :param slugs: Ordered cart slugs to store.
    :type slugs: list[str]
    :returns: ``None``.
    :rtype: None
    """
    request.session[CART_SESSION_KEY] = list(slugs)
    request.session.modified = True


def add_product(request, product):
    """Add a product to the cart if it is not already present.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :param product: Product to add.
    :type product: shop.models.Product
    :returns: ``None``.
    :rtype: None
    """
    slugs = get_cart_slugs(request)
    if product.slug not in slugs:
        slugs.append(product.slug)
        save_cart_slugs(request, slugs)


def remove_product(request, product):
    """Remove a product from the cart.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :param product: Product to remove.
    :type product: shop.models.Product
    :returns: ``None``.
    :rtype: None
    """
    slugs = [slug for slug in get_cart_slugs(request) if slug != product.slug]
    save_cart_slugs(request, slugs)


def clear_cart(request):
    """Empty the cart after a successful checkout.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: ``None``.
    :rtype: None
    """
    if CART_SESSION_KEY in request.session:
        del request.session[CART_SESSION_KEY]
        request.session.modified = True


def get_cart_products(request):
    """Return published products in the same order as the session cart.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: Ordered published products.
    :rtype: list[shop.models.Product]
    """
    slugs = get_cart_slugs(request)
    if not slugs:
        return []

    products_by_slug = {
        product.slug: product
        for product in Product.objects.filter(is_published=True, slug__in=slugs)
    }
    return [products_by_slug[slug] for slug in slugs if slug in products_by_slug]


def build_cart_summary(request):
    """Build the cart payload used by templates and JSON responses.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :returns: Structured cart summary for rendering.
    :rtype: dict[str, object]
    """
    products = get_cart_products(request)
    owned_slugs = get_owned_product_slugs(request.user, slugs=[product.slug for product in products])
    subtotal = sum((product.price for product in products), Decimal("0.00"))
    items = []

    for product in products:
        items.append(
            {
                "slug": product.slug,
                "title": product.title,
                "artist_name": product.artist_name,
                "meta": product.meta,
                "price": str(product.price),
                "price_display": product.price_display,
                "art_path": product.art_path,
                "art_url": product.art_url,
                "art_alt": product.art_alt or product.title,
                "remove_url": reverse("shop:cart_remove", kwargs={"slug": product.slug}),
            }
        )

    owned_titles = [item["title"] for item in items if item["slug"] in owned_slugs]
    if len(owned_titles) == 1:
        ownership_message = f'You already bought "{owned_titles[0]}". It is ready in your account.'
    elif owned_titles:
        ownership_message = "Some tracks in this cart are already in your account. Remove them before checking out."
    else:
        ownership_message = ""

    return {
        "items": items,
        "item_count": len(items),
        "subtotal": str(subtotal),
        "subtotal_display": f"£{subtotal:.2f}",
        "is_empty": len(items) == 0,
        "owned_item_slugs": sorted(owned_slugs),
        "has_owned_items": bool(owned_titles),
        "ownership_message": ownership_message,
        "checkout_url": reverse("shop:checkout"),
        "account_url": reverse("shop:account"),
    }
