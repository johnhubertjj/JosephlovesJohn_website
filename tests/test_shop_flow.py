"""Integration tests for the reusable shop flow."""

import json
import re
import sys
from decimal import Decimal
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest
import stripe as stripe_sdk
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, override_settings
from django.urls import reverse
from shop import views as shop_views
from shop.models import CustomerProfile, Order, OrderItem, Product

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

VALID_CHECKOUT_CONSENTS = {
    "accept_terms": "on",
}


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


@pytest.fixture(autouse=True)
def ensure_seeded_download_assets(create_static_asset) -> None:
    """Create temporary storefront audio files so checkout tests don't rely on local ignored media."""
    for download_path in Product.objects.values_list("download_file_path", flat=True):
        create_static_asset(download_path, content=b"shop audio")
    wav_paths = Product.objects.exclude(download_file_wav_path="").values_list("download_file_wav_path", flat=True)
    for download_path in wav_paths:
        create_static_asset(download_path, content=b"shop wav audio")


@pytest.fixture(autouse=True)
def clear_public_rate_limits() -> None:
    """Reset cache-backed rate limit state between shop-flow tests."""
    cache.clear()
    yield
    cache.clear()


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


def test_get_stripe_module_requires_installed_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Checkout setup should fail clearly when Stripe is unavailable."""
    monkeypatch.setattr(shop_views, "stripe", None)

    with pytest.raises(ImproperlyConfigured, match="Stripe is not installed"):
        shop_views._get_stripe_module()


def test_get_stripe_module_requires_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Checkout setup should fail clearly when the Stripe secret key is missing."""
    stripe_module = SimpleNamespace(api_key=None, api_version=None)
    monkeypatch.setattr(shop_views, "stripe", stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_SECRET_KEY", "")

    with pytest.raises(ImproperlyConfigured, match="Set STRIPE_SECRET_KEY"):
        shop_views._get_stripe_module()


def test_get_stripe_module_configures_the_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Checkout setup should propagate the configured API credentials to Stripe."""
    stripe_module = SimpleNamespace(api_key=None, api_version=None)
    monkeypatch.setattr(shop_views, "stripe", stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setattr(shop_views.settings, "STRIPE_API_VERSION", "2026-01-01")

    configured_module = shop_views._get_stripe_module()

    assert configured_module is stripe_module
    assert stripe_module.api_key == "sk_test_123"
    assert stripe_module.api_version == "2026-01-01"


def test_stripe_value_falls_back_to_attribute_lookup_when_getter_signature_is_narrower() -> None:
    """Stripe helper access should support test doubles with single-argument getters."""

    class NarrowGetter:
        name = "attribute value"

        def get(self, key):  # noqa: ANN001 - intentionally mirrors a narrow third-party getter
            return f"getter:{key}"

    assert shop_views._stripe_value(NarrowGetter(), "name", "fallback") == "attribute value"


def test_stripe_value_returns_default_when_value_is_none() -> None:
    """Stripe helper access should gracefully handle null values."""
    assert shop_views._stripe_value(None, "name", "fallback") == "fallback"


def test_stripe_value_reads_stripe_sdk_objects_without_get_method() -> None:
    """Stripe helper access should support Stripe SDK objects backed by _data."""
    checkout_session = stripe_sdk.checkout.Session.construct_from(
        {"metadata": {"order_id": "21"}},
        "sk_test_123",
    )

    assert shop_views._stripe_value(checkout_session, "metadata", {}) == checkout_session.metadata


def test_stripe_identifier_supports_expandable_objects() -> None:
    """Stripe identifier helpers should read IDs from expandable objects."""
    assert shop_views._stripe_identifier(SimpleNamespace(id="pi_test_123")) == "pi_test_123"


@pytest.mark.django_db
def test_apply_paid_checkout_session_supports_nested_stripe_sdk_objects() -> None:
    """Paid session synchronization should handle Stripe SDK metadata/detail objects."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("2.00"),
        total=Decimal("2.00"),
        status=Order.Status.PENDING,
    )
    checkout_session = stripe_sdk.checkout.Session.construct_from(
        {
            "id": "cs_test_nested",
            "status": "complete",
            "payment_status": "paid",
            "metadata": {"order_id": str(order.pk)},
            "customer_details": {"name": "Updated Buyer", "email": "updated@example.com"},
            "payment_intent": "pi_test_123",
        },
        "sk_test_123",
    )

    order_was_just_confirmed = shop_views._apply_paid_checkout_session_to_order(order, checkout_session)

    order.refresh_from_db()
    assert order_was_just_confirmed is True
    assert order.full_name == "Updated Buyer"
    assert order.email == "updated@example.com"
    assert order.stripe_payment_intent_id == "pi_test_123"
    assert order.is_paid is True


def test_sync_customer_profile_from_order_updates_profile_and_email(django_user_model) -> None:
    """Confirmed orders should refresh the saved profile name and login email."""
    user = django_user_model.objects.create_user(
        username="shopper",
        email="old@example.com",
        password="secret123",
    )
    profile = CustomerProfile.objects.create(user=user, full_name="Old Name", marketing_opt_in=True)
    order = Order.objects.create(
        user=user,
        full_name="Updated Name",
        email="new@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
    )

    shop_views._sync_customer_profile_from_order(order)

    profile.refresh_from_db()
    user.refresh_from_db()
    assert profile.full_name == "Updated Name"
    assert profile.marketing_opt_in is True
    assert user.email == "new@example.com"


def test_sync_customer_profile_from_order_ignores_guest_orders() -> None:
    """Guest orders should not attempt profile synchronization."""
    guest_order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
    )

    shop_views._sync_customer_profile_from_order(guest_order)

    assert CustomerProfile.objects.count() == 0


def test_fulfill_checkout_session_returns_none_without_required_identifiers() -> None:
    """Webhook fulfillment should ignore sessions that do not name an order and session."""
    assert shop_views._fulfill_checkout_session({"metadata": {}}) is None
    assert shop_views._fulfill_checkout_session({"id": "cs_test_missing", "metadata": {}}) is None


def test_fulfill_checkout_session_returns_none_for_unknown_orders() -> None:
    """Webhook fulfillment should ignore sessions that do not match a pending order."""
    assert (
        shop_views._fulfill_checkout_session({"id": "cs_test_unknown", "metadata": {"order_id": "99999"}}) is None
    )


def test_login_view_redirects_to_next_parameter_after_success(client, django_user_model) -> None:
    """Returning listeners should be redirected to their requested next page after login."""
    django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )

    response = client.post(
        reverse("shop:login") + f"?next={reverse('shop:checkout')}",
        {"username": "listener", "password": "secret123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("shop:checkout")


def test_login_page_links_to_password_reset(client) -> None:
    """The shop login page should link to the password reset flow."""
    response = client.get(reverse("shop:login"))

    assert response.status_code == 200
    assert reverse("shop:password_reset") in response.content.decode()


def test_login_shows_username_error_when_account_is_unknown(client) -> None:
    """Unknown usernames should show a field-level error below the username input."""
    response = client.post(
        reverse("shop:login"),
        {"username": "missing-user", "password": "secret123"},
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "That username is not recognised." in body
    assert "That password is incorrect." not in body


def test_login_shows_password_error_when_password_is_wrong(client, django_user_model) -> None:
    """Known usernames with a bad password should show a field-level password error."""
    django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )

    response = client.post(
        reverse("shop:login"),
        {"username": "listener", "password": "wrong-password"},
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "That password is incorrect." in body
    assert "That username is not recognised." not in body


def test_login_rate_limit_blocks_repeated_attempts(client, django_user_model) -> None:
    """Repeated login attempts should be rate limited with a user-facing message."""
    django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )

    with override_settings(LOGIN_RATE_LIMIT_ATTEMPTS=1, LOGIN_RATE_LIMIT_WINDOW=300):
        first_response = client.post(reverse("shop:login"), {"username": "listener", "password": "wrong-password"})
        second_response = client.post(reverse("shop:login"), {"username": "listener", "password": "wrong-password"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert "Too many login attempts" in second_response.content.decode()


def test_logout_requires_post_and_redirects_back_to_music_page(client, django_user_model) -> None:
    """Logging out should require POST and return listeners to the music section."""
    user = django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )
    client.force_login(user)

    get_response = client.get(reverse("shop:logout"))
    response = client.post(reverse("shop:logout"))

    assert get_response.status_code == 405
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("main_site:music")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
)
def test_password_reset_sends_email_for_known_account(client, django_user_model) -> None:
    """Known customer emails should receive a reset message."""
    django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )

    response = client.post(reverse("shop:password_reset"), {"email": "listener@example.com"})

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("shop:password_reset_done")
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.to == ["listener@example.com"]
    assert "Reset your JosephlovesJohn password" in sent_email.subject
    assert "/shop/reset/" in sent_email.body


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    SITE_URL="https://josephlovesjohn.com",
)
def test_password_reset_uses_the_canonical_site_url(client, django_user_model) -> None:
    """Password reset emails should use the configured public domain."""
    django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )

    client.post(reverse("shop:password_reset"), {"email": "listener@example.com"})

    assert len(mail.outbox) == 1
    assert "https://josephlovesjohn.com/shop/reset/" in mail.outbox[0].body


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
)
def test_password_reset_rate_limit_blocks_repeated_attempts(client, django_user_model) -> None:
    """Repeated password reset requests should be rate limited."""
    django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )

    with override_settings(PASSWORD_RESET_RATE_LIMIT_ATTEMPTS=1, PASSWORD_RESET_RATE_LIMIT_WINDOW=3600):
        first_response = client.post(reverse("shop:password_reset"), {"email": "listener@example.com"})
        second_response = client.post(reverse("shop:password_reset"), {"email": "listener@example.com"})

    assert first_response.status_code == 302
    assert second_response.status_code == 200
    assert "Too many reset requests" in second_response.content.decode()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
)
def test_password_reset_confirm_updates_password(client, django_user_model) -> None:
    """Customers should be able to set a new password from the emailed reset link."""
    user = django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="old-password-123",
    )
    client.post(reverse("shop:password_reset"), {"email": "listener@example.com"})

    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    match = re.search(r"https?://[^/\s]+(?P<path>/shop/reset/[^/\s]+/[^/\s]+/)", body)
    assert match is not None

    confirm_path = match.group("path")
    confirm_response = client.get(confirm_path)
    set_password_path = confirm_response.headers["Location"]
    complete_response = client.post(
        set_password_path,
        {
            "new_password1": "new-SuperSafePass123",
            "new_password2": "new-SuperSafePass123",
        },
    )
    user.refresh_from_db()

    assert confirm_response.status_code == 302
    assert set_password_path.endswith("/set-password/")
    assert complete_response.status_code == 302
    assert complete_response.headers["Location"] == reverse("shop:password_reset_complete")
    assert user.check_password("new-SuperSafePass123") is True


def test_checkout_get_redirects_empty_cart_back_to_music(client) -> None:
    """Empty carts should not enter the checkout flow from a GET request."""
    response = client.get(reverse("shop:checkout"))

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("main_site:music")


def test_checkout_post_redirects_empty_cart_back_to_music(client) -> None:
    """Empty carts should not enter the checkout flow from a POST request."""
    response = client.post(reverse("shop:checkout"))

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("main_site:music")


def test_checkout_get_redirects_authenticated_user_to_stripe_with_saved_email(
    client, django_user_model, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Logged-in listeners should carry their saved email into Stripe checkout."""
    user = django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )
    CustomerProfile.objects.create(user=user, full_name="Jayne Listener")
    client.force_login(user)
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    review_response = client.get(reverse("shop:checkout"))
    response = client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)

    order = Order.objects.get()

    assert review_response.status_code == 200
    assert response.status_code == 302
    assert response.headers["Location"] == "https://checkout.stripe.test/cs_test_1"
    assert order.full_name == "Jayne Listener"
    assert order.email == "listener@example.com"
    assert fake_stripe_checkout["created_payloads"][0]["customer_email"] == "listener@example.com"


def test_checkout_get_renders_review_page_before_redirect_to_stripe(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Opening checkout should render the review page before payment starts."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.get(reverse("shop:checkout"))

    assert response.status_code == 200
    assert Order.objects.count() == 0
    assert "Continue to Stripe Checkout" in response.content.decode()


def test_checkout_post_redirects_to_stripe_checkout(client, seeded_product: Product, fake_stripe_checkout) -> None:
    """Posting valid acknowledgements should create the Stripe Checkout session."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)

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


def test_checkout_uses_the_canonical_site_url_for_stripe_redirects(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Stripe success and cancel URLs should use the configured public domain."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    with override_settings(SITE_URL="https://josephlovesjohn.com"):
        client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)

    checkout_payload = fake_stripe_checkout["created_payloads"][0]
    assert checkout_payload["success_url"].startswith("https://josephlovesjohn.com/shop/success/")
    assert checkout_payload["cancel_url"] == "https://josephlovesjohn.com/shop/checkout/?canceled=1"


def test_checkout_post_requires_digital_download_acknowledgements(client, seeded_product: Product) -> None:
    """Checkout should not start until the required legal acknowledgements are confirmed."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.post(reverse("shop:checkout"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "This field is required." in body
    assert Order.objects.count() == 0


def test_checkout_post_blocks_payment_when_a_download_is_unavailable(client, seeded_product: Product) -> None:
    """Checkout should fail closed before Stripe when the file is not available to deliver."""
    seeded_product.download_file_wav_path = "audio/missing-before-payment.wav"
    seeded_product.save(update_fields=["download_file_wav_path"])
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    response = client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)
    body = response.content.decode()

    assert response.status_code == 200
    assert "A download is unavailable" in body
    assert "checkout has been paused" in body
    assert Order.objects.count() == 0


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    BUSINESS_CONTACT_EMAIL="josephlovesjohn@gmail.com",
)
def test_success_page_confirms_paid_stripe_session_and_clears_cart(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """The success page should verify the Stripe session before unlocking downloads."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))
    client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)
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
    assert order.confirmation_email_sent_at is not None
    assert client.session.get("shop_cart") in (None, [])
    assert client.session["shop_recent_orders"][0] == order.pk
    assert seeded_product.title in response.content.decode()
    assert len(mail.outbox) == 1
    assert f"order #{order.pk}" in mail.outbox[0].subject.lower()
    assert reverse("shop:download", args=[order.items.get().pk]) in mail.outbox[0].body
    assert "format=wav" in mail.outbox[0].body


def test_register_rejects_duplicate_email_addresses(client, django_user_model) -> None:
    """Registration should not allow multiple accounts to share the same email address."""
    django_user_model.objects.create_user(
        username="existing-listener",
        email="listener@example.com",
        password="secret123",
    )

    response = client.post(
        reverse("shop:register"),
        {
            "username": "new-listener",
            "email": "listener@example.com",
            "full_name": "New Listener",
            "password1": "EvenSaferPass123",
            "password2": "EvenSaferPass123",
        },
    )

    assert response.status_code == 200
    assert "An account with that email address already exists." in response.content.decode()


def test_success_page_syncs_authenticated_customer_profile_from_verified_stripe_session(
    client, django_user_model, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Verified Stripe returns should refresh the signed-in buyer's saved details."""
    user = django_user_model.objects.create_user(
        username="listener",
        email="listener@example.com",
        password="secret123",
    )
    CustomerProfile.objects.create(user=user, full_name="Old Profile Name")
    client.force_login(user)
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))
    client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)
    order = Order.objects.get()

    fake_stripe_checkout["sessions"]["cs_test_1"].update(
        {
            "status": "complete",
            "payment_status": "paid",
            "payment_intent": "pi_test_456",
            "customer_details": {
                "name": "Updated Listener",
                "email": "updated@example.com",
            },
        }
    )

    response = client.get(reverse("shop:success", args=[order.pk]), {"session_id": "cs_test_1"})

    order.refresh_from_db()
    user.refresh_from_db()
    profile = CustomerProfile.objects.get(user=user)
    assert response.status_code == 200
    assert order.status == Order.Status.CONFIRMED
    assert profile.full_name == "Updated Listener"
    assert user.email == "updated@example.com"


def test_success_page_still_allows_guest_after_webhook_confirmation(
    client, seeded_product: Product, fake_stripe_checkout
) -> None:
    """Webhook-confirmed guest orders should still unlock on the Stripe redirect."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))
    client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)
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


def test_checkout_renders_config_error_and_deletes_pending_order(
    client, seeded_product: Product, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stripe config errors should fall back to the checkout page without leaving stray orders."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    def raise_config_error():
        raise ImproperlyConfigured("Checkout is not configured yet.")

    monkeypatch.setattr(shop_views, "_get_stripe_module", raise_config_error)

    response = client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)

    assert response.status_code == 200
    assert "Checkout is not configured yet." in response.content.decode()
    assert Order.objects.count() == 0


def test_checkout_renders_generic_error_and_deletes_pending_order(
    client, seeded_product: Product, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unexpected checkout failures should show the generic retry message and delete the pending order."""
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))

    def raise_runtime_error(self, request, order):  # noqa: ANN001 - Django view method signature
        raise RuntimeError("stripe unavailable")

    monkeypatch.setattr(shop_views.CheckoutView, "_create_checkout_session", raise_runtime_error)

    response = client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)
    body = response.content.decode()

    assert response.status_code == 200
    assert "Stripe checkout could not be started right now. Please try again in a moment." in body
    assert Order.objects.count() == 0


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
        download_file_wav_path=seeded_product.download_file_wav_path,
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
        download_file_wav_path=seeded_product.download_file_wav_path,
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


def test_success_page_rejects_unpaid_order_without_a_verified_session(client, seeded_product: Product) -> None:
    """Pending orders should stay hidden until Stripe verification occurs."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
        status=Order.Status.PENDING,
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


def test_success_page_rejects_authenticated_orders_for_the_wrong_user(
    client, django_user_model, seeded_product: Product
) -> None:
    """Signed-in orders should only be visible to the owning account."""
    owner = django_user_model.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="secret123",
    )
    intruder = django_user_model.objects.create_user(
        username="intruder",
        email="intruder@example.com",
        password="secret123",
    )
    order = Order.objects.create(
        user=owner,
        full_name="Owner",
        email="owner@example.com",
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
    client.force_login(intruder)

    response = client.get(reverse("shop:success", args=[order.pk]))

    assert response.status_code == 404


def test_success_page_allows_the_signed_in_owner_without_guest_session_state(
    client, django_user_model, seeded_product: Product
) -> None:
    """Signed-in owners should not need the guest-session allowlist to view their order."""
    owner = django_user_model.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="secret123",
    )
    order = Order.objects.create(
        user=owner,
        full_name="Owner",
        email="owner@example.com",
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
    client.force_login(owner)

    response = client.get(reverse("shop:success", args=[order.pk]))

    assert response.status_code == 200
    assert seeded_product.title in response.content.decode()


def test_success_page_rejects_mismatched_stripe_session_id(client, seeded_product: Product) -> None:
    """Success pages should reject redirects that do not match the stored Stripe session ID."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
        status=Order.Status.PENDING,
        stripe_checkout_session_id="cs_expected",
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

    response = client.get(reverse("shop:success", args=[order.pk]), {"session_id": "cs_other"})

    assert response.status_code == 404


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    BUSINESS_CONTACT_EMAIL="josephlovesjohn@gmail.com",
)
def test_signed_email_download_link_allows_guest_access_without_recent_session(
    client, seeded_product: Product, fake_stripe_checkout, create_private_download_asset
) -> None:
    """The emailed download link should work even without the original guest session."""
    create_private_download_asset(seeded_product.download_file_path, content=b"paid file")
    create_private_download_asset(seeded_product.download_file_wav_path, content=b"paid wav file")
    client.post(reverse("shop:cart_add", args=[seeded_product.slug]))
    client.post(reverse("shop:checkout"), VALID_CHECKOUT_CONSENTS)
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

    assert response.status_code == 200
    assert len(mail.outbox) == 1

    download_line = next(line for line in mail.outbox[0].body.splitlines() if "/shop/download/" in line)
    signed_download = urlsplit(download_line.strip())

    fresh_client = Client()
    signed_response = fresh_client.get(f"{signed_download.path}?{signed_download.query}")

    assert signed_response.status_code == 200
    assert signed_response.get("Content-Disposition", "").startswith("attachment;")

    wav_download_line = next(
        line for line in mail.outbox[0].body.splitlines() if "/shop/download/" in line and "format=wav" in line
    )
    wav_signed_download = urlsplit(wav_download_line.strip().split("WAV: ", 1)[-1])
    wav_response = fresh_client.get(f"{wav_signed_download.path}?{wav_signed_download.query}")

    assert wav_response.status_code == 200
    assert 'filename="' in wav_response.get("Content-Disposition", "")


@pytest.mark.parametrize("event_type", ["checkout.session.completed", "checkout.session.async_payment_succeeded"])
@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    BUSINESS_CONTACT_EMAIL="josephlovesjohn@gmail.com",
)
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
        download_file_wav_path=seeded_product.download_file_wav_path,
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
    assert order.confirmation_email_sent_at is not None
    assert len(mail.outbox) == 1


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    BUSINESS_CONTACT_EMAIL="josephlovesjohn@gmail.com",
)
def test_webhook_and_success_page_do_not_send_duplicate_download_emails(
    client, seeded_product: Product, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A webhook and the redirect page should cooperate without double-emailing the customer."""
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
                "type": "checkout.session.completed",
                "data": {"object": checkout_session},
            }
        ),
        checkout=SimpleNamespace(
            Session=SimpleNamespace(
                retrieve=lambda session_id, expand=None: SimpleNamespace(**checkout_session),  # noqa: ARG005
            )
        ),
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    webhook_response = client.post(
        reverse("shop:stripe_webhook"),
        data=json.dumps({"id": "evt_test"}).encode(),
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=test",
    )
    success_response = client.get(reverse("shop:success", args=[order.pk]), {"session_id": "cs_test_webhook"})
    order.refresh_from_db()

    assert webhook_response.status_code == 200
    assert success_response.status_code == 200
    assert order.confirmation_email_sent_at is not None
    assert len(mail.outbox) == 1


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


def test_stripe_webhook_rejects_requests_when_no_secret_is_configured(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Webhook endpoints should fail closed when signature verification is unavailable."""
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "")

    response = client.post(
        reverse("shop:stripe_webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="bad",
    )

    assert response.status_code == 400


def test_stripe_webhook_ignores_unrelated_event_types(client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-checkout events should be acknowledged without mutating orders."""
    stripe_module = SimpleNamespace(
        Webhook=SimpleNamespace(
            construct_event=lambda payload, sig_header, secret: {  # noqa: ARG005
                "type": "customer.created",
                "data": {"object": {"id": "cus_test"}},
            }
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    response = client.post(
        reverse("shop:stripe_webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=test",
    )

    assert response.status_code == 200
    assert Order.objects.count() == 0


def test_stripe_webhook_ignores_checkout_events_for_missing_orders(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signed webhook events should be tolerated even when no matching order exists."""
    stripe_module = SimpleNamespace(
        Webhook=SimpleNamespace(
            construct_event=lambda payload, sig_header, secret: {  # noqa: ARG005
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_missing",
                        "status": "complete",
                        "payment_status": "paid",
                        "payment_intent": "pi_missing",
                        "metadata": {"order_id": "99999"},
                    }
                },
            }
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    response = client.post(
        reverse("shop:stripe_webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=test",
    )

    assert response.status_code == 200


def test_stripe_webhook_tolerates_checkout_events_that_fail_final_verification(
    client, seeded_product: Product, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signed checkout events should be acknowledged even when payment verification fails."""
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=seeded_product.price,
        total=seeded_product.price,
        status=Order.Status.PENDING,
        stripe_checkout_session_id="cs_bad_status",
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
    stripe_module = SimpleNamespace(
        Webhook=SimpleNamespace(
            construct_event=lambda payload, sig_header, secret: {  # noqa: ARG005
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_bad_status",
                        "status": "open",
                        "payment_status": "unpaid",
                        "payment_intent": None,
                        "metadata": {"order_id": str(order.pk)},
                    }
                },
            }
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)
    monkeypatch.setattr(shop_views.settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    response = client.post(
        reverse("shop:stripe_webhook"),
        data=b"{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=1,v1=test",
    )
    order.refresh_from_db()

    assert response.status_code == 200
    assert order.status == Order.Status.PENDING


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
        download_file_wav_path=seeded_product.download_file_wav_path,
    )
    client.force_login(user)

    response = client.get(reverse("shop:account"))
    body = response.content.decode()

    assert response.status_code == 200
    assert f"Order #{order.id}" in body
    assert seeded_product.title in body
    assert reverse("shop:download", args=[order.items.get().pk]) in body
    assert "Download WAV" in body


def test_guest_download_requires_recent_session_order(
    client, seeded_product: Product, create_private_download_asset
) -> None:
    """Guest downloads should only work from the same session that paid."""
    create_private_download_asset(seeded_product.download_file_path, content=b"paid file")
    order = Order.objects.create(
        full_name="Guest Buyer",
        email="guest@example.com",
        subtotal=Decimal("1.00"),
        total=Decimal("1.00"),
    )
    item = OrderItem.objects.create(
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

    blocked = client.get(reverse("shop:download", args=[item.pk]))
    assert blocked.status_code == 404

    session = client.session
    session["shop_recent_orders"] = [order.pk]
    session.save()

    allowed = client.get(reverse("shop:download", args=[item.pk]))
    assert allowed.status_code == 200
    assert allowed.get("Content-Disposition", "").startswith("attachment;")


def test_account_owner_can_download_private_file(
    client, django_user_model, seeded_product: Product, create_private_download_asset
) -> None:
    """Authenticated owners should be able to fetch their private downloads."""
    create_private_download_asset(seeded_product.download_file_path, content=b"private bytes")
    user = django_user_model.objects.create_user(
        username="collector",
        email="collector@example.com",
        password="secret123",
    )
    order = Order.objects.create(
        user=user,
        full_name="Collector",
        email="collector@example.com",
        subtotal=seeded_product.price,
        total=seeded_product.price,
    )
    item = OrderItem.objects.create(
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

    response = client.get(reverse("shop:download", args=[item.pk]))

    assert response.status_code == 200
    assert response.get("Content-Disposition", "").startswith("attachment;")


def test_account_owner_can_download_bundled_static_file_when_private_storage_is_unset(
    client, django_user_model, seeded_product: Product
) -> None:
    """Authenticated owners should still receive repo-tracked audio files when no private store is configured."""
    user = django_user_model.objects.create_user(
        username="collector",
        email="collector@example.com",
        password="secret123",
    )
    order = Order.objects.create(
        user=user,
        full_name="Collector",
        email="collector@example.com",
        subtotal=seeded_product.price,
        total=seeded_product.price,
    )
    item = OrderItem.objects.create(
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

    response = client.get(reverse("shop:download", args=[item.pk]))

    assert response.status_code == 200
    assert response.get("Content-Disposition", "").startswith("attachment;")


def test_private_download_route_redirects_to_presigned_r2_url(
    client, django_user_model, seeded_product: Product, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Authorized download requests should redirect to a short-lived R2 URL when configured."""
    user = django_user_model.objects.create_user(
        username="collector",
        email="collector@example.com",
        password="secret123",
    )
    order = Order.objects.create(
        user=user,
        full_name="Collector",
        email="collector@example.com",
        subtotal=seeded_product.price,
        total=seeded_product.price,
    )
    item = OrderItem.objects.create(
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

    class FakeS3Client:
        def generate_presigned_url(self, operation, Params, ExpiresIn):  # noqa: N803 - boto shape
            assert operation == "get_object"
            assert Params["Key"] == seeded_product.download_file_path
            assert ExpiresIn == 120
            return "https://signed.example.com/private-download"

    fake_boto3 = SimpleNamespace(client=lambda *args, **kwargs: FakeS3Client())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setattr(shop_views.settings, "PRIVATE_DOWNLOADS_BUCKET_NAME", "jlj-private")
    monkeypatch.setattr(
        shop_views.settings,
        "PRIVATE_DOWNLOADS_ENDPOINT_URL",
        "https://example-account.r2.cloudflarestorage.com",
    )
    monkeypatch.setattr(shop_views.settings, "PRIVATE_DOWNLOADS_ACCESS_KEY_ID", "key")
    monkeypatch.setattr(shop_views.settings, "PRIVATE_DOWNLOADS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(shop_views.settings, "PRIVATE_DOWNLOADS_REGION", "auto")
    monkeypatch.setattr(shop_views.settings, "PRIVATE_DOWNLOADS_KEY_PREFIX", "")
    monkeypatch.setattr(shop_views.settings, "PRIVATE_DOWNLOADS_URL_EXPIRY", 120)

    response = client.get(reverse("shop:download", args=[item.pk]))

    assert response.status_code == 302
    assert response.headers["Location"] == "https://signed.example.com/private-download"
