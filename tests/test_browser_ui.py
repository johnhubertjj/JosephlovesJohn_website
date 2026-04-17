"""Browser-level tests for the main site, shop, and mastering UI flows."""

from __future__ import annotations

import random
import re
from types import SimpleNamespace

import pytest
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from shop import views as shop_views
from shop.models import Product

pytestmark = [pytest.mark.browser, pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def _route_url(live_server, route_name: str, *args, **kwargs) -> str:
    """Build an absolute route URL for Playwright browser tests."""
    return f"{live_server.url}{reverse(route_name, args=args, kwargs=kwargs)}"


@pytest.fixture(autouse=True)
def ensure_browser_shop_download_assets(create_private_download_asset) -> None:
    """Create temporary private audio files so browser checkout can reach the review page."""
    for download_path in Product.objects.values_list("download_file_path", flat=True):
        create_private_download_asset(download_path, content=b"browser audio")


@pytest.fixture
def mobile_browser_page(playwright_browser):
    """Create a mobile-sized browser page and fail on uncaught page errors."""
    context = playwright_browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        has_touch=True,
    )
    page = context.new_page()
    page.set_default_timeout(20_000)
    page_errors: list[str] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    try:
        yield page
    finally:
        context.close()
        assert not page_errors, f"Unexpected browser page errors: {page_errors}"


def test_intro_route_sets_hash_and_activates_intro_article(browser_page, live_server) -> None:
    """The intro route should land the user directly in the intro article."""
    browser_page.goto(_route_url(live_server, "main_site:intro"), wait_until="load")
    browser_page.wait_for_selector("article#intro.active")

    assert browser_page.evaluate("window.location.hash") == "#intro"
    assert browser_page.locator("article#intro.active").is_visible()
    assert browser_page.locator(".intro-signup-form").is_visible()
    assert browser_page.locator("[data-cookie-banner]").is_visible()
    assert browser_page.locator("[data-cookie-essential-only]").is_visible()
    assert browser_page.locator("[data-cookie-accept-all]").is_visible()


def test_music_share_modal_supports_copy_dialog_interaction_and_escape(browser_page, live_server) -> None:
    """The share modal should open, stay open during dialog clicks, and close on escape."""
    browser_page.add_init_script(
        """
        Object.defineProperty(window.navigator, 'clipboard', {
            configurable: true,
            value: { writeText: () => Promise.resolve() }
        });
        """
    )
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    trigger = browser_page.locator(".music-share-trigger").first
    trigger.click()

    modal = browser_page.locator("#music-share-modal")
    modal.wait_for()
    assert modal.get_attribute("aria-hidden") == "false"
    first_title = browser_page.locator(".music-library-item h3").first.inner_text().strip().lower()
    assert browser_page.locator("#music-share-title").inner_text().strip().lower() == first_title
    assert browser_page.locator("#music-share-link").input_value().endswith("/music/")

    browser_page.locator(".music-share-dialog").click()
    assert "/music/" in browser_page.url
    assert modal.get_attribute("aria-hidden") == "false"

    browser_page.locator("[data-share-copy]").click()
    browser_page.locator("[data-share-copy-label]").wait_for()
    assert browser_page.locator("[data-share-copy-label]").inner_text().strip().lower() == "copied"

    browser_page.keyboard.press("Escape")
    browser_page.wait_for_function(
        "document.getElementById('music-share-modal').getAttribute('aria-hidden') === 'true'"
    )


def test_music_cart_modal_supports_add_remove_and_checkout(browser_page, live_server) -> None:
    """The cart UI should open from a track card, update counts, and link to checkout."""
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    cart_button = browser_page.locator("#floating-cart-button")
    assert cart_button.is_hidden()

    browser_page.locator(".music-buy-trigger").first.click()

    cart_modal = browser_page.locator("#music-cart-modal")
    cart_modal.wait_for()
    assert cart_modal.get_attribute("aria-hidden") == "false"
    assert cart_button.is_visible()
    assert browser_page.locator("[data-cart-count]").first.inner_text().strip() == "1"
    assert browser_page.locator(".music-cart-item").count() == 1

    checkout_link = browser_page.locator("[data-cart-checkout]")
    assert (checkout_link.get_attribute("href") or "").endswith("/shop/checkout/")

    browser_page.locator(".music-cart-remove").click()
    browser_page.wait_for_function("document.querySelectorAll('.music-cart-item').length === 0")
    browser_page.wait_for_function("document.getElementById('floating-cart-button').classList.contains('is-hidden')")


def test_music_purchase_path_reaches_checkout_and_cart_persists(browser_page, live_server) -> None:
    """Adding a track from the music page should reach checkout and keep the cart intact on return."""
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    first_title = browser_page.locator(".music-library-item h3").first.inner_text().strip()
    browser_page.locator(".music-buy-trigger").first.click()
    browser_page.locator("#music-cart-modal").wait_for()
    browser_page.locator("[data-cart-checkout]").click()
    browser_page.wait_for_url("**/shop/checkout/")

    assert browser_page.locator("h1").inner_text().strip().lower() == "secure checkout"
    assert first_title in browser_page.locator(".shop-order-item").first.inner_text()
    assert browser_page.locator("[data-checkout-submit]").is_disabled()

    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")
    browser_page.locator("#floating-cart-button").click()
    browser_page.locator("#music-cart-modal").wait_for()

    assert browser_page.locator(".music-cart-item").count() == 1
    assert first_title.lower() in browser_page.locator(".music-cart-item").first.inner_text().lower()


def test_art_lightbox_supports_backdrop_and_escape_close(browser_page, live_server) -> None:
    """The art lightbox should open from gallery items and close via overlay and escape."""
    browser_page.goto(_route_url(live_server, "main_site:art"), wait_until="load")
    browser_page.wait_for_selector("article#art.active")

    gig_photo = browser_page.locator(".gig-photo-card").first
    gig_photo.click()

    lightbox = browser_page.locator("#art-lightbox")
    lightbox.wait_for()
    assert lightbox.get_attribute("aria-hidden") == "false"
    lightbox_src = browser_page.locator(".art-lightbox-image").get_attribute("src") or ""
    assert "/static/images/gig_photos/" in lightbox_src or "/media/gig_photos/" in lightbox_src
    assert browser_page.locator(".art-lightbox-caption").inner_text().strip()

    lightbox.click(position={"x": 8, "y": 8})
    browser_page.wait_for_function(
        "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'true'"
    )

    browser_page.locator(".album-art-card a[data-art-lightbox='image']").first.click()
    assert lightbox.get_attribute("aria-hidden") == "false"
    browser_page.keyboard.press("Escape")
    browser_page.wait_for_function(
        "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'true'"
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
)
def test_shop_register_and_login_flows(browser_page, live_server) -> None:
    """Registration and returning-login flows should work in a real browser."""
    browser_page.goto(_route_url(live_server, "shop:register"), wait_until="load")
    browser_page.locator('input[name="username"]').fill("browserlistener")
    browser_page.locator('input[name="email"]').fill("browserlistener@example.com")
    browser_page.locator('input[name="full_name"]').fill("Browser Listener")
    browser_page.locator('input[name="password1"]').fill("SuperSafePass123")
    browser_page.locator('input[name="password2"]').fill("SuperSafePass123")
    browser_page.locator('button[type="submit"]').click()
    browser_page.wait_for_url("**/shop/account/")

    assert browser_page.locator("h1").inner_text().strip().lower() == "your account"
    assert "Browser Listener" in browser_page.content()

    browser_page.locator('a[href="/shop/logout/"]').click()
    browser_page.wait_for_url("**/music/**")

    browser_page.goto(_route_url(live_server, "shop:login"), wait_until="load")
    browser_page.locator('input[name="username"]').fill("browserlistener")
    browser_page.locator('input[name="password"]').fill("wrong-password")
    browser_page.locator('button[type="submit"]').click()
    assert browser_page.locator(".shop-field-error").last.inner_text().strip() == "That password is incorrect."

    browser_page.locator('input[name="password"]').fill("SuperSafePass123")
    browser_page.locator('button[type="submit"]').click()
    browser_page.wait_for_url("**/shop/account/")
    assert "Browser Listener" in browser_page.content()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
)
def test_shop_password_reset_flow(browser_page, live_server, django_user_model) -> None:
    """The forgot-password journey should email a reset link and accept the new password."""
    mail.outbox.clear()
    django_user_model.objects.create_user(
        username="resetlistener",
        email="resetlistener@example.com",
        password="OldPass123",
    )

    browser_page.goto(_route_url(live_server, "shop:login"), wait_until="load")
    browser_page.locator('a[href="/shop/password-reset/"]').click()
    browser_page.wait_for_url("**/shop/password-reset/")
    browser_page.locator('input[name="email"]').fill("resetlistener@example.com")
    browser_page.locator('button[type="submit"]').click()
    browser_page.wait_for_url("**/shop/password-reset/done/")

    assert "Check your email" in browser_page.content()
    assert len(mail.outbox) == 1

    match = re.search(
        rf"{re.escape(live_server.url)}(?P<path>/shop/reset/[^/\s]+/[^/\s]+/)",
        mail.outbox[0].body,
    )
    assert match is not None

    browser_page.goto(f"{live_server.url}{match.group('path')}", wait_until="load")
    browser_page.locator('input[name="new_password1"]').fill("EvenSaferPass456")
    browser_page.locator('input[name="new_password2"]').fill("EvenSaferPass456")
    browser_page.locator('button[type="submit"]').click()
    browser_page.wait_for_url("**/shop/reset/complete/")

    assert "Password updated" in browser_page.content()

    browser_page.get_by_role("link", name="Return to login").click()
    browser_page.wait_for_url("**/shop/login/")
    browser_page.locator('input[name="username"]').fill("resetlistener")
    browser_page.locator('input[name="password"]').fill("EvenSaferPass456")
    browser_page.locator('button[type="submit"]').click()
    browser_page.wait_for_url("**/shop/account/")
    assert "resetlistener@example.com" in browser_page.content()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    BUSINESS_CONTACT_EMAIL="josephlovesjohn@gmail.com",
)
def test_paid_checkout_success_page_sends_email_and_allows_download_via_signed_link(
    browser_page,
    live_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A browser checkout should land on the success page, send the email, and honor the signed download link."""
    mail.outbox.clear()
    browser_page.set_default_timeout(10_000)

    created_payloads: list[dict[str, object]] = []
    sessions: dict[str, dict[str, object]] = {}

    def create(**kwargs):
        created_payloads.append(kwargs)
        order_id = kwargs["metadata"]["order_id"]
        session_id = f"cs_browser_{len(created_payloads)}"
        session = {
            "id": session_id,
            "url": (
                f"{live_server.url}"
                f"{reverse('shop:success', kwargs={'order_id': order_id})}"
                f"?session_id={session_id}"
            ),
            "status": "complete",
            "payment_status": "paid",
            "payment_intent": f"pi_browser_{len(created_payloads)}",
            "metadata": kwargs.get("metadata", {}),
            "customer_details": {
                "name": "Browser Buyer",
                "email": "browserbuyer@example.com",
            },
        }
        sessions[session_id] = session
        return SimpleNamespace(id=session_id, url=session["url"])

    def retrieve(session_id, expand=None):  # noqa: ARG001 - mirrors Stripe's SDK signature
        return SimpleNamespace(**sessions[session_id])

    stripe_module = SimpleNamespace(
        checkout=SimpleNamespace(
            Session=SimpleNamespace(
                create=create,
                retrieve=retrieve,
            )
        )
    )
    monkeypatch.setattr(shop_views, "_get_stripe_module", lambda: stripe_module)

    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    chosen_title = browser_page.locator(".music-library-item h3").first.inner_text().strip()
    browser_page.locator(".music-buy-trigger").first.click()
    browser_page.locator("#music-cart-modal").wait_for()
    browser_page.locator("[data-cart-checkout]").click()
    browser_page.wait_for_url("**/shop/checkout/")

    browser_page.locator("#id_accept_terms").check()
    browser_page.locator("[data-checkout-submit]").click()
    browser_page.wait_for_function("window.location.pathname.includes('/shop/success/')")
    browser_page.wait_for_load_state("load")

    assert browser_page.locator("h1").inner_text().strip().lower() == "order confirmed"
    assert browser_page.locator(".shop-inline-note").inner_text().strip() == (
        "A download email has been sent to browserbuyer@example.com."
    )
    assert chosen_title.lower() in browser_page.locator(".shop-download-list").inner_text().lower()
    assert browser_page.locator(".shop-download-list .button").first.is_visible()
    assert "/shop/download/" in (
        browser_page.locator(".shop-download-list .button").first.get_attribute("href") or ""
    )
    assert len(created_payloads) == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["browserbuyer@example.com"]

    match = re.search(
        rf"{re.escape(live_server.url)}(?P<path>/shop/download/\d+/\?access=[^\s]+)",
        mail.outbox[0].body,
    )
    assert match is not None

    signed_download_response = Client().get(match.group("path"))
    assert signed_download_response.status_code == 200
    assert signed_download_response.get("Content-Disposition", "").startswith("attachment;")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
)
def test_contact_form_browser_flow_covers_validation_and_success(browser_page, live_server) -> None:
    """The contact page should show validation feedback and then submit successfully."""
    mail.outbox.clear()

    browser_page.goto(_route_url(live_server, "main_site:contact"), wait_until="load")
    browser_page.wait_for_selector("article#contact.active")

    browser_page.locator('input[name="name"]').fill("Browser Tester")
    browser_page.locator('input[name="email"]').fill("not-an-email")
    browser_page.locator('textarea[name="message"]').fill("Hello from the browser test.")
    browser_page.locator("[data-analytics-contact-form]").evaluate("(form) => form.submit()")
    browser_page.wait_for_url("**/contact/**")
    browser_page.wait_for_selector("article#contact.active")

    assert "Please correct the highlighted fields and try again." in browser_page.content()
    assert "Enter a valid email address." in browser_page.content()
    assert len(mail.outbox) == 0

    browser_page.locator('input[name="email"]').fill("browser@example.com")
    browser_page.locator("[data-analytics-contact-form]").evaluate("(form) => form.submit()")
    browser_page.wait_for_url("**/contact/**")
    browser_page.wait_for_selector("article#contact.active")

    assert "Thanks, your message has been sent." in browser_page.content()
    assert len(mail.outbox) == 1


def test_mobile_viewport_supports_music_cart_art_lightbox_and_navigation(
    mobile_browser_page,
    live_server,
) -> None:
    """Key main-site interactions should still work at a mobile viewport."""
    mobile_browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    mobile_browser_page.wait_for_selector("article#music.active")

    mobile_browser_page.locator(".music-buy-trigger").first.click()
    mobile_browser_page.locator("#music-cart-modal").wait_for()
    assert mobile_browser_page.locator("#floating-cart-button").is_visible()
    mobile_browser_page.locator("[data-cart-close]").first.click()
    mobile_browser_page.wait_for_function(
        "document.getElementById('music-cart-modal').getAttribute('aria-hidden') === 'true'"
    )

    mobile_browser_page.goto(_route_url(live_server, "main_site:art"), wait_until="load")
    mobile_browser_page.wait_for_selector("article#art.active")
    mobile_browser_page.locator(".gig-photo-card").first.click()
    mobile_browser_page.locator("#art-lightbox").wait_for()
    assert mobile_browser_page.locator("#art-lightbox").get_attribute("aria-hidden") == "false"
    mobile_browser_page.keyboard.press("Escape")
    mobile_browser_page.wait_for_function(
        "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'true'"
    )


def test_mastering_route_and_menu_open_still_work(browser_page, live_server) -> None:
    """The mastering route should still load and expose the menu UI."""
    browser_page.goto(_route_url(live_server, "mastering:home") + "?from_home=1", wait_until="load")

    body_class = browser_page.locator("body").get_attribute("class") or ""
    assert "is-from-home" in body_class

    browser_page.locator("a.mastering-menu-trigger").click()
    browser_page.wait_for_function("document.body.classList.contains('is-menu-visible')")
    assert browser_page.locator("#menu .close").is_visible()
    assert browser_page.locator('#menu a[href="#services"]').is_visible()


def test_legal_links_open_routed_legal_page(browser_page, live_server) -> None:
    """Policy links should navigate to the standalone legal route."""
    browser_page.goto(_route_url(live_server, "main_site:privacy"), wait_until="load")

    assert browser_page.url.endswith("/privacy/")
    assert browser_page.locator(".legal-card").is_visible()
    assert browser_page.locator("#footer").is_visible()

    browser_page.locator(".legal-back-link").click()
    browser_page.wait_for_load_state("load")
    assert browser_page.url.rstrip("/") == live_server.url.rstrip("/")


def test_seeded_random_clicks_do_not_break_the_site(browser_page, live_server) -> None:
    """Deterministic random clicks across the active music pane should not break the app shell."""
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    article = browser_page.locator("article#music.active")
    box = article.bounding_box()
    assert box is not None

    generator = random.Random(20260417)
    performed_clicks = 0
    for _ in range(24):
        x = int(generator.uniform(box["x"] + 24, box["x"] + box["width"] - 24))
        y = int(generator.uniform(box["y"] + 24, box["y"] + min(box["height"], 700) - 24))
        target_state = browser_page.evaluate(
            """
            (point) => {
                const target = document.elementFromPoint(point.x, point.y);
                if (!target) {
                    return { clickable: false };
                }
                const blockedAncestor = target.closest('a, button, input, textarea, select, label');
                return {
                    clickable: !blockedAncestor && target.tagName !== 'IFRAME'
                };
            }
            """,
            {"x": x, "y": y},
        )
        if not target_state["clickable"]:
            continue

        browser_page.mouse.click(x, y)
        performed_clicks += 1
        browser_page.wait_for_timeout(40)

    assert performed_clicks >= 10
    assert browser_page.url.startswith(live_server.url)

    browser_page.keyboard.press("Escape")
    browser_page.keyboard.press("Escape")

    assert browser_page.locator("#wrapper").is_visible()
    assert browser_page.locator("#footer").is_visible()
