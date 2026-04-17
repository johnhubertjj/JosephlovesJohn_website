"""Helpers for determining whether a signed-in listener already owns products."""

from .models import Order, OrderItem


def get_owned_product_slugs(user, *, slugs=None):
    """Return confirmed purchased product slugs for the given user."""
    if not getattr(user, "is_authenticated", False):
        return set()

    queryset = OrderItem.objects.filter(
        order__user=user,
        order__status=Order.Status.CONFIRMED,
    )
    if slugs is not None:
        queryset = queryset.filter(product__slug__in=slugs)

    return set(queryset.values_list("product__slug", flat=True).distinct())
