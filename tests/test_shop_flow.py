"""Integration tests for the reusable shop flow."""

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from shop import views as shop_views
from shop.models import CustomerProfile, Order, OrderItem, Product

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def seeded_product() -> Product:
    """Return the first seeded shop product.

    :returns: Published seeded product.
    :rtype: shop.models.Product
    """
    return Product.objects.order_by("sort_order", "id").first()


@pytest.fixture
def fake_stripe_checkout(monkeypatch: pytest.MonkeyPatch):
    """Stub Stripe Checkout session creation and retrieval for integration tests."""

    created_payloads: list[dict[str, object]] = []
    sessions: dict[str, dict[str, object]] = {}

    def create(**kwargs):
        created_payloads.append(kwargs)
        session_id = f"cs_test_{len(created_payloads)}"
        session = {
            "id": session_id,
            "url": f"https://checkout.stripe.test/{session_id}",
            "status": "open",
            "payment_status": "unpaid",
            "payment_intent": None,
            "metadata": kwargs.get("metadata", {}),
        }
        sessions[session_id] = session
        return SimpleNamespace(**session)

    def retrieve(session_id, expand=None):  # noqa: ARG001 - mirrors Stripe's SDK signature
        session = sessions[session_id]
        return SimpleNamespace(**session)

    stripe_module = SimpleNamespace(
        checkout=SimpleNamespace(
            Session=SimpleNamespace(
                create=create,
                retrieve=retrieve,
            )
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    return {"created_payloads": created_payloads, "sessions": sessions}


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


def test_checkout_get_redirects_authenticated_user_to_stripe_with_saved_email(
    client, django_user_model, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Logged-in listeners should be sent straight to Stripe with their email attached."""
    user = django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )
    CustomerProfile.objects.create(user=user, full_name="Jayne Listener")
    client.force_login(user)
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.get(reverse("shop:checkout"))

    order = Order.objects.get()

    assert response.status_code == 302
    assert response.headers["Location"] == "https://checkout.stripe.test/cs_test_1"
    assert order.full_name == "Jayne Listener"
    assert order.email == "listener@example.com"
    assert fake_stripe_checkout["created_payloads"][0]["customer_email"] == "listener@example.com"


def test_checkout_get_redirects_to_stripe_checkout(client, seeded_product: Product, fake_stripe_checkout) -> None:
    """Opening checkout should create a pending order and redirect to Stripe Checkout."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.get(reverse("shop:checkout"))

    order = Order.objects.get()
    item = order.items.get()
    checkout_payload = fake_stripe_checkout["created_payloads"][0]

    assert response.status_code == 302
    assert response.headers["Location"] == "https://checkout.stripe.test/cs_test_1"
    assert order.full_name == "Guest checkout"
    assert order.email == ""
    assert order.status == Order.Status.PENDING
    assert order.total == seeded_product.price
    assert order.stripe_checkout_session_id == "cs_test_1"
    assert item.title_snapshot == seeded_product.title
    assert item.meta_snapshot == seeded_product.meta
    assert item.art_path_snapshot == seeded_product.art_path
    assert client.session["shop_cart"] == [seeded_product.slug]
    assert client.session.get("shop_recent_orders") in (None, [])
    assert checkout_payload["mode"] == "payment"
    assert checkout_payload["metadata"] == {"order_id": str(order.pk)}
    assert checkout_payload["line_items"][0]["price_data"]["currency"] == "gbp"
    assert "customer_email" not in checkout_payload


def test_success_page_confirms_paid_stripe_session_and_clears_cart(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """The success page should verify the Stripe session before unlocking downloads."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))
    client.get(reverse("shop:checkout"))
    order = Order.objects.get()

    fake_stripe_checkout["sessions"]["cs_test_1"].update(
        {
            "status": "complete",
            "payment_status": "paid",
            "payment_intent": "pi_test_123",
            "customer_details": {
                "name": "Portfolio Buyer",
                "email": "buyer@example.com",
            },
        }
    )

    response = client.get(reverse("shop:success", args=[order.pk]), {"session_id": "cs_test_1"})
    order.refresh_from_db()

    assert response.status_code == 200
    assert order.full_name == "Portfolio Buyer"
    assert order.email == "buyer@example.com"
    assert order.status == Order.Status.CONFIRMED
    assert order.stripe_payment_intent_id == "pi_test_123"
    assert order.paid_at is not None
    assert client.session.get("shop_cart") in (None, [])
    assert client.session["shop_recent_orders"][0] == order.pk
    assert seeded_product.title in response.content.decode()


def test_success_page_still_allows_guest_after_webhook_confirmation(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Webhook-confirmed guest orders should still unlock on the Stripe redirect."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))
    client.get(reverse("shop:checkout"))
    order = Order.objects.get()

    fake_stripe_checkout["sessions"]["cs_test_1"].update(
        {
            "status": "complete",
            "payment_status": "paid",
            "payment_intent": "pi_test_123",
            "customer_details": {
                "name": "Webhook Buyer",
                "email": "webhook@example.com",
            },
        }
    )
    order.mark_paid(payment_intent_id="pi_test_123")
    order.full_name = "Webhook Buyer"
    order.email = "webhook@example.com"
    order.save(update_fields=["full_name", "email", "status", "stripe_payment_intent_id", "paid_at"])

    response = client.get(reverse("shop:success", args=[order.pk]), {"session_id": "cs_test_1"})

    assert response.status_code == 200
    assert client.session["shop_recent_orders"][0] == order.pk
    assert seeded_product.title in response.content.decode()


def test_canceled_checkout_renders_retry_page(client, seeded_product: Product) -> None:
    """Returning from a canceled Stripe checkout should show a visible retry state."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.get(reverse("shop:checkout"), {"canceled": "1"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "Checkout canceled" in body
    assert "Continue to Stripe Checkout" in body


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


def test_pending_guest_success_page_requires_verified_stripe_session(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Pending guest orders should stay locked until Stripe confirms the session."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
        status=Order.Status.PENDING,
        stripe_checkout_session_id="cs_test_pending",
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
    fake_stripe_checkout["sessions"]["cs_test_pending"] = {
        "id": "cs_test_pending",
        "status": "open",
        "payment_status": "unpaid",
        "payment_intent": None,
        "metadata": {"order_id": str(order.pk)},
    }

    response = client.get(reverse("shop:success", args=[order.pk]), {"session_id": "cs_test_pending"})

    assert response.status_code == 404


@pytest.mark.parametrize("event_type", ["checkout.session.completed", "checkout.session.async_payment_succeeded"])
def test_stripe_webhook_confirms_matching_order(
    client, seeded_product: Product, monkeypatch: pytest.MonkeyPatch, event_type: str
) -> None:
    """Signed webhook events should mark the matching order paid."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=seeded_product.price,
        total=seeded_product.price,
        status=Order.Status.PENDING,
        stripe_checkout_session_id="cs_test_webhook",
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

    checkout_session = {
        "id": "cs_test_webhook",
        "status": "complete",
        "payment_status": "paid",
        "payment_intent": "pi_webhook_123",
        "customer_details": {
            "name": "Webhook Buyer",
            "email": "webhook@example.com",
        },
        "metadata": {"order_id": str(order.pk)},
    }

    stripe_module = SimpleNamespace(
        Webhook=SimpleNamespace(
            construct_event=lambda payload, sig_header, secret: {  # noqa: ARG005
                "type": event_type,
                "data": {"object": checkout_session},
            }
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    response = client.post(
        reverse("shop:stripe_webhook"),
        data=json.dumps({"id": "evt_test"}).encode(),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=test",
    )
    order.refresh_from_db()

    assert response.status_code == 200
    assert order.status == Order.Status.CONFIRMED
    assert order.full_name == "Webhook Buyer"
    assert order.email == "webhook@example.com"
    assert order.stripe_payment_intent_id == "pi_webhook_123"


def test_stripe_webhook_rejects_invalid_signature(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Invalid webhook signatures should be rejected."""
    stripe_module = SimpleNamespace(
        Webhook=SimpleNamespace(
            construct_event=lambda payload, sig_header, secret: (_ for _ in ()).throw(ValueError("bad signature"))
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    response = client.post(
        reverse("shop:stripe_webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="bad",
    )

    assert response.status_code == 400


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
