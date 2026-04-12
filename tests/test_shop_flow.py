"""Integration tests for the reusable shop flow."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from shop.models import CustomerProfile, Order, OrderItem, Product

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def seeded_product() -> Product:
    """Return the first seeded shop product.

    :returns: Published seeded product.
    :rtype: shop.models.Product
    """
    return Product.objects.order_by("sort_order", "id").first()


def test_cart_add_and_remove_endpoints_return_updated_summary(client, seeded_product: Product) -> None:
    """Adding and removing a product should update the JSON cart summary."""
    add_response = client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    assert add_response.status_code == 200
    add_payload = add_response.json()
    assert add_payload["item_count"] == 1
    assert add_payload["items"][0]["slug"] == seeded_product.slug
    assert add_payload["subtotal_display"] == seeded_product.price_display

    remove_response = client.post(reverse("shop:cart_remove", args=[seeded_product.slug]))

    assert remove_response.status_code == 200
    remove_payload = remove_response.json()
    assert remove_payload["item_count"] == 0
    assert remove_payload["is_empty"] is True


def test_checkout_prefills_authenticated_user_details(
    client, django_user_model, seeded_product: Product
) -> None:
    """Logged-in listeners should see their saved details prefilled at checkout."""
    user = django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )
    CustomerProfile.objects.create(user=user, full_name="Jayne Listener")
    client.force_login(user)
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.get(reverse("shop:checkout"))

    assert response.status_code == 200
    assert response.context["form"].initial["full_name"] == "Jayne Listener"
    assert response.context["form"].initial["email"] == "listener@example.com"
    assert response.context["form"].initial["save_details"] is True


def test_checkout_post_creates_order_and_clears_cart(client, seeded_product: Product) -> None:
    """Submitting checkout should create an order, snapshot its items, and empty the cart."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.post(
        reverse("shop:checkout"),
        data={
            "full_name": "Portfolio Buyer",
            "email": "buyer@example.com",
            "notes": "Please keep me posted about future releases.",
            "save_details": "",
        },
    )

    order = Order.objects.get()
    item = order.items.get()

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("shop:success", args=[order.pk])
    assert order.full_name == "Portfolio Buyer"
    assert order.email == "buyer@example.com"
    assert order.total == seeded_product.price
    assert item.title_snapshot == seeded_product.title
    assert item.meta_snapshot == seeded_product.meta
    assert item.art_path_snapshot == seeded_product.art_path
    assert client.session.get("shop_cart") in (None, [])
    assert client.session["shop_recent_orders"][0] == order.pk


def test_guest_success_page_requires_recent_session_order(client, seeded_product: Product) -> None:
    """Guest order success pages should only be visible from the same session."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
    )
    OrderItem.objects.create(
        order=order,
        product=seeded_product,
        title_snapshot=seeded_product.title,
        artist_snapshot=seeded_product.artist_name,
        meta_snapshot=seeded_product.meta,
        price_snapshot=seeded_product.price,
        art_path_snapshot=seeded_product.art_path,
        art_alt_snapshot=seeded_product.art_alt,
        download_file_path=seeded_product.download_file_path,
    )

    response = client.get(reverse("shop:success", args=[order.pk]))
    assert response.status_code == 404

    session = client.session
    session["shop_recent_orders"] = [order.pk]
    session.save()

    allowed_response = client.get(reverse("shop:success", args=[order.pk]))
    assert allowed_response.status_code == 200
    assert seeded_product.title in allowed_response.content.decode()


def test_register_view_creates_profile_and_logs_user_in(client) -> None:
    """Registering should create the account, attach a profile, and sign the user in."""
    response = client.post(
        reverse("shop:register"),
        data={
            "username": "newlistener",
            "email": "newlistener@example.com",
            "full_name": "New Listener",
            "password1": "SuperSafePass123",
            "password2": "SuperSafePass123",
        },
    )

    user_model = get_user_model()
    user = user_model.objects.get(username="newlistener")

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("shop:account")
    assert CustomerProfile.objects.get(user=user).full_name == "New Listener"
    assert client.session.get("_auth_user_id") == str(user.pk)


def test_account_requires_authentication(client) -> None:
    """The account dashboard should redirect anonymous visitors to login."""
    response = client.get(reverse("shop:account"))

    assert response.status_code == 302
    assert response.headers["Location"].startswith(reverse("shop:login"))


def test_account_lists_completed_order_downloads(client, django_user_model, seeded_product: Product) -> None:
    """The account page should show a logged-in user's previous download links."""
    user = django_user_model.objects.create_user(
        username="collector",
        email="collector@example.com",
        password="secret123",
    )
    CustomerProfile.objects.create(user=user, full_name="Collector")
    order = Order.objects.create(
        user=user,
        full_name="Collector",
        email="collector@example.com",
        subtotal=seeded_product.price,
        total=seeded_product.price,
    )
    OrderItem.objects.create(
        order=order,
        product=seeded_product,
        title_snapshot=seeded_product.title,
        artist_snapshot=seeded_product.artist_name,
        meta_snapshot=seeded_product.meta,
        price_snapshot=seeded_product.price,
        art_path_snapshot=seeded_product.art_path,
        art_alt_snapshot=seeded_product.art_alt,
        download_file_path=seeded_product.download_file_path,
    )
    client.force_login(user)

    response = client.get(reverse("shop:account"))
    body = response.content.decode()

    assert response.status_code == 200
    assert f"Order #{order.id}" in body
    assert seeded_product.title in body
    assert seeded_product.download_file_path in body
