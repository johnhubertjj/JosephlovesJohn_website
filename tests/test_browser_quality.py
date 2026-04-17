"""Broader browser-quality coverage for payments, accessibility, layout, and consent."""

from __future__ import annotations

import os
import random
import re
from types import SimpleNamespace

import pytest
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from shop import views as shop_views
from shop.models import Order, Product

pytestmark = [pytest.mark.browser, pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def _route_url(live_server, route_name: str, *args, **kwargs) -> str:
    """Build an absolute route URL for Playwright browser tests."""
    return f"{live_server.url}{reverse(route_name, args=args, kwargs=kwargs)}"


@pytest.fixture(autouse=True)
def ensure_browser_quality_shop_download_assets(create_private_download_asset) -> None:
    """Create private audio files so payment/browser paths can exercise real delivery code."""
    for download_path in Product.objects.values_list("download_file_path", flat=True):
        create_private_download_asset(download_path, content=b"browser quality audio")


def _active_element_matches(page, selector: str) -> bool:
    """Return whether the currently focused element matches the selector."""
    return bool(
        page.evaluate(
            """
            (cssSelector) => {
                const activeElement = document.activeElement;
                return !!activeElement && activeElement.matches(cssSelector);
            }
            """,
            selector,
        )
    )


def _current_focus_is_within(page, selector: str) -> bool:
    """Return whether the currently focused element is inside the selector."""
    return bool(
        page.evaluate(
            """
            (cssSelector) => {
                const activeElement = document.activeElement;
                return !!activeElement && !!activeElement.closest(cssSelector);
            }
            """,
            selector,
        )
    )


def _layout_metrics(page, selector: str) -> dict[str, float]:
    """Return viewport and element bounds for layout regression assertions."""
    metrics = page.evaluate(
        """
        (cssSelector) => {
            const element = document.querySelector(cssSelector);
            if (!element) {
                return null;
            }

            const rect = element.getBoundingClientRect();
            return {
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight,
                scrollWidth: document.documentElement.scrollWidth,
                scrollHeight: document.documentElement.scrollHeight,
                x: rect.x,
                y: rect.y,
                width: rect.width,
                height: rect.height,
                right: rect.right,
                bottom: rect.bottom
            };
        }
        """,
        selector,
    )
    assert metrics is not None
    return metrics


def _safe_random_click(page, generator: random.Random, selector: str) -> bool:
    """Click a random safe point inside the selector, skipping obvious interactive controls."""
    target = page.locator(selector)
    box = target.bounding_box()
    assert box is not None

    for _ in range(8):
        x = int(generator.uniform(box["x"] + 24, box["x"] + box["width"] - 24))
        y = int(generator.uniform(box["y"] + 24, box["y"] + min(box["height"], 700) - 24))
        target_state = page.evaluate(
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

        page.mouse.click(x, y)
        page.wait_for_timeout(40)
        return True

    return False


def _stub_kit_embed(route) -> None:
    """Fulfill the Kit embed script with a deterministic local test stub."""
    route.fulfill(
        status=200,
        content_type="application/javascript",
        body="""
            (function () {
                var root = document.querySelector('[data-signup-embed]');
                if (!root) {
                    return;
                }

                root.innerHTML = ''
                    + '<form class="formkit-form">'
                    + '<input class="formkit-input" type="email" />'
                    + '<button class="formkit-submit" type="submit">Join</button>'
                    + '</form>';
            })();
        """,
    )


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
    BUSINESS_CONTACT_EMAIL="josephlovesjohn@gmail.com",
)
def test_webhook_first_browser_success_flow_sends_one_email_and_unlocks_success_page(
    browser_page,
    live_server,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Webhook-first fulfillment should show the success page without sending duplicate emails."""
    mail.outbox.clear()

    created_payloads: list[dict[str, object]] = []
    sessions: dict[str, dict[str, object]] = {}
    webhook_session: dict[str, object] = {}

    def construct_event(payload, sig_header, secret):  # noqa: ANN001 - Stripe-compatible test stub
        return {
            "type": "checkout.session.completed",
            "data": {"object": webhook_session["session"]},
        }

    def create(**kwargs):
        created_payloads.append(kwargs)
        order_id = kwargs["metadata"]["order_id"]
        session_id = f"cs_webhook_browser_{len(created_payloads)}"
        session = {
            "id": session_id,
            "url": (
                f"{live_server.url}"
                f"{reverse('shop:success', kwargs={'order_id': order_id})}"
                f"?session_id={session_id}"
            ),
            "status": "complete",
            "payment_status": "paid",
            "payment_intent": f"pi_webhook_browser_{len(created_payloads)}",
            "metadata": kwargs.get("metadata", {}),
            "customer_details": {
                "name": "Webhook Browser Buyer",
                "email": "webhookbrowser@example.com",
            },
        }
        sessions[session_id] = session
        webhook_session["session"] = session

        order = Order.objects.get(pk=order_id)
        order.stripe_checkout_session_id = session_id
        order.save(update_fields=["stripe_checkout_session_id"])

        webhook_response = Client().post(
            reverse("shop:stripe_webhook"),
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig_test_browser",
        )
        assert webhook_response.status_code == 200
        return SimpleNamespace(id=session_id, url=session["url"])

    def retrieve(session_id, expand=None):  # noqa: ARG001 - mirrors Stripe's SDK signature
        return SimpleNamespace(**sessions[session_id])

    stripe_module = SimpleNamespace(
        checkout=SimpleNamespace(
            Session=SimpleNamespace(
                create=create,
                retrieve=retrieve,
            )
        ),
        Webhook=SimpleNamespace(construct_event=construct_event),
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

    assert browser_page.locator(".shop-inline-note").inner_text().strip() == (
        "A download email has been sent to webhookbrowser@example.com."
    )
    assert chosen_title.lower() in browser_page.locator(".shop-download-list").inner_text().lower()
    assert len(created_payloads) == 1
    assert len(mail.outbox) == 1

    order = Order.objects.get()
    assert order.confirmation_email_sent_at is not None
    assert order.status == Order.Status.CONFIRMED


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="sales@josephlovesjohn.com",
)
def test_cookie_preference_flow_controls_optional_signup_embed(browser_page, live_server) -> None:
    """Cookie preferences should persist, reopen, and drive the optional Kit embed state."""
    browser_page.set_default_timeout(10_000)
    browser_page.route("https://josephlovesjohn.kit.com/**", _stub_kit_embed)
    browser_page.goto(_route_url(live_server, "main_site:intro"), wait_until="load")
    browser_page.wait_for_selector("article#intro.active")

    browser_page.locator("[data-cookie-essential-only]").click()
    browser_page.wait_for_function(
        """
        () => {
            const banner = document.querySelector('[data-cookie-banner]');
            return !!banner && banner.hidden === true;
        }
        """
    )
    assert browser_page.locator("html").get_attribute("data-cookie-preference") == "essential"
    assert "site_cookie_preference=essential" in browser_page.evaluate("document.cookie")

    browser_page.locator("[data-cookie-manage]").click()
    browser_page.wait_for_function(
        """
        () => {
            const banner = document.querySelector('[data-cookie-banner]');
            return !!banner && banner.hidden === false;
        }
        """
    )
    browser_page.locator("[data-cookie-accept-all]").click()
    browser_page.wait_for_function(
        """
        () => {
            const form = document.querySelector('.formkit-form');
            return !!form;
        }
        """
    )
    browser_page.wait_for_function(
        """
        () => {
            const root = document.querySelector('[data-signup-root]');
            const gate = document.querySelector('[data-signup-gate]');
            return !!root && root.classList.contains('is-signup-live') && !!gate && gate.hidden === true;
        }
        """
    )
    assert browser_page.locator("html").get_attribute("data-cookie-preference") == "all"

    browser_page.locator("[data-cookie-manage]").click()
    browser_page.locator("[data-cookie-essential-only]").click()
    browser_page.wait_for_function(
        """
        () => {
            const gate = document.querySelector('[data-signup-gate]');
            const embed = document.querySelector('[data-signup-embed]');
            return !!gate && gate.hidden === false && !!embed && embed.childElementCount === 0;
        }
        """
    )


def test_keyboard_focus_accessibility_across_share_cart_and_lightbox(browser_page, live_server) -> None:
    """Core dialogs should support keyboard open/close, focus entry, focus trapping, and focus return."""
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    share_trigger = browser_page.locator(".music-share-trigger").first
    share_trigger.focus()
    share_trigger.press("Enter")
    browser_page.locator("#music-share-modal").wait_for()

    assert _active_element_matches(browser_page, "[data-share-close]")
    browser_page.keyboard.press("Shift+Tab")
    assert _active_element_matches(browser_page, "[data-share-copy]")
    browser_page.keyboard.press("Tab")
    assert _active_element_matches(browser_page, "[data-share-close]")
    browser_page.keyboard.press("Escape")
    browser_page.wait_for_function(
        "document.getElementById('music-share-modal').getAttribute('aria-hidden') === 'true'"
    )
    assert _active_element_matches(browser_page, ".music-share-trigger")

    buy_trigger = browser_page.locator(".music-buy-trigger").first
    buy_trigger.focus()
    buy_trigger.press("Enter")
    browser_page.locator("#music-cart-modal").wait_for()

    assert _active_element_matches(browser_page, ".music-cart-close")
    browser_page.keyboard.press("Shift+Tab")
    assert _current_focus_is_within(browser_page, ".music-cart-dialog")
    browser_page.keyboard.press("Escape")
    browser_page.wait_for_function(
        "document.getElementById('music-cart-modal').getAttribute('aria-hidden') === 'true'"
    )
    assert _active_element_matches(browser_page, ".music-buy-trigger")

    browser_page.goto(_route_url(live_server, "main_site:art"), wait_until="load")
    browser_page.wait_for_selector("article#art.active")

    lightbox_trigger = browser_page.locator('[data-art-lightbox="image"]').first
    lightbox_trigger.focus()
    lightbox_trigger.press("Enter")
    browser_page.locator("#art-lightbox").wait_for()

    assert _active_element_matches(browser_page, "[data-art-close]")
    browser_page.keyboard.press("Tab")
    assert _active_element_matches(browser_page, "[data-art-close]")
    browser_page.keyboard.press("Escape")
    browser_page.wait_for_function(
        "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'true'"
    )
    assert _active_element_matches(browser_page, '[data-art-lightbox="image"]')


def test_visual_layout_regression_guard_for_music_checkout_and_legal(browser_page, live_server) -> None:
    """Key routes should stay within the viewport and avoid obvious layout drift."""
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    music_metrics = _layout_metrics(browser_page, "article#music.active")
    assert music_metrics["scrollWidth"] <= music_metrics["viewportWidth"] + 4
    assert music_metrics["x"] >= -4
    assert music_metrics["right"] <= music_metrics["viewportWidth"] + 4

    browser_page.locator(".music-buy-trigger").first.click()
    browser_page.locator("#music-cart-modal").wait_for()
    cart_metrics = _layout_metrics(browser_page, ".music-cart-dialog")
    assert cart_metrics["width"] <= cart_metrics["viewportWidth"] + 4
    assert cart_metrics["x"] >= -4
    assert cart_metrics["right"] <= cart_metrics["viewportWidth"] + 4
    assert cart_metrics["bottom"] <= cart_metrics["viewportHeight"] + 24

    browser_page.locator("[data-cart-checkout]").click()
    browser_page.wait_for_url("**/shop/checkout/")
    checkout_metrics = _layout_metrics(browser_page, ".shop-grid")
    assert checkout_metrics["scrollWidth"] <= checkout_metrics["viewportWidth"] + 4
    assert checkout_metrics["width"] <= checkout_metrics["viewportWidth"] + 4

    browser_page.goto(_route_url(live_server, "main_site:privacy"), wait_until="load")
    legal_metrics = _layout_metrics(browser_page, ".legal-card")
    assert legal_metrics["scrollWidth"] <= legal_metrics["viewportWidth"] + 4
    assert legal_metrics["x"] >= -4
    assert legal_metrics["right"] <= legal_metrics["viewportWidth"] + 4
    assert legal_metrics["height"] > 200


def test_longer_deterministic_fuzz_session_preserves_shell_under_mixed_actions(browser_page, live_server) -> None:
    """A longer deterministic browser fuzz session should not break the app shell."""
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")

    generator = random.Random(20260417)
    actions_taken = 0

    def action_music_safe_click() -> None:
        browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
        browser_page.wait_for_selector("article#music.active")
        assert _safe_random_click(browser_page, generator, "article#music.active")

    def action_share_modal() -> None:
        browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
        browser_page.wait_for_selector("article#music.active")
        browser_page.locator(".music-share-trigger").first.click()
        browser_page.locator("#music-share-modal").wait_for()
        browser_page.keyboard.press("Escape")

    def action_cart_modal() -> None:
        browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
        browser_page.wait_for_selector("article#music.active")
        browser_page.locator(".music-buy-trigger").first.click()
        browser_page.locator("#music-cart-modal").wait_for()
        browser_page.keyboard.press("Escape")

    def action_art_lightbox() -> None:
        browser_page.goto(_route_url(live_server, "main_site:art"), wait_until="load")
        browser_page.wait_for_selector("article#art.active")
        browser_page.locator(".gig-photo-card").first.click()
        browser_page.locator("#art-lightbox").wait_for()
        browser_page.keyboard.press("Escape")

    def action_legal_roundtrip() -> None:
        browser_page.goto(_route_url(live_server, "main_site:privacy"), wait_until="load")
        browser_page.locator(".legal-back-link").click()
        browser_page.wait_for_load_state("load")

    action_pool = [
        action_music_safe_click,
        action_share_modal,
        action_cart_modal,
        action_art_lightbox,
        action_legal_roundtrip,
    ]

    for _ in range(30):
        generator.choice(action_pool)()
        browser_page.keyboard.press("Escape")
        assert browser_page.url.startswith(live_server.url)
        assert browser_page.locator("#wrapper").is_visible()
        assert browser_page.locator("#footer").count() == 1
        actions_taken += 1

    assert actions_taken == 30


def test_real_hosted_stripe_page_round_trip_in_browser(browser_page, live_server) -> None:
    """Opt-in smoke test for the real Stripe-hosted checkout page in browser test mode."""
    if os.environ.get("RUN_REAL_STRIPE_BROWSER") != "1":
        pytest.skip("Set RUN_REAL_STRIPE_BROWSER=1 to exercise the real hosted Stripe page.")

    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key.startswith("sk_test_"):
        pytest.skip("A Stripe test secret key is required for the real hosted checkout browser test.")

    browser_page.set_default_timeout(20_000)
    browser_page.goto(_route_url(live_server, "main_site:music"), wait_until="load")
    browser_page.wait_for_selector("article#music.active")
    browser_page.locator(".music-buy-trigger").first.click()
    browser_page.locator("#music-cart-modal").wait_for()
    browser_page.locator("[data-cart-checkout]").click()
    browser_page.wait_for_url("**/shop/checkout/")

    browser_page.locator("#id_accept_terms").check()
    browser_page.locator("[data-checkout-submit]").click()
    browser_page.wait_for_url(re.compile(r"https://checkout\.stripe\.com/.*"))

    email_candidates = [
        browser_page.locator('input[name="email"]').first,
        browser_page.get_by_label("Email").first,
    ]
    for locator in email_candidates:
        try:
            locator.wait_for(timeout=2_000)
            locator.fill("browserbuyer@example.com")
            break
        except Exception:  # pragma: no cover - only used for the opt-in Stripe-hosted run.
            continue
    else:  # pragma: no cover - only used for the opt-in Stripe-hosted run.
        pytest.skip("Stripe Checkout email field could not be located in the hosted page.")

    try:  # pragma: no cover - only used for the opt-in Stripe-hosted run.
        browser_page.frame_locator('iframe[title*="card number"]').locator("input").fill("4242424242424242")
        browser_page.frame_locator('iframe[title*="expiration"]').locator("input").fill("1234")
        browser_page.frame_locator('iframe[title*="CVC"]').locator("input").fill("123")
        postcode_frame = browser_page.frame_locator('iframe[title*="postal"]').locator("input")
        if postcode_frame.count():
            postcode_frame.fill("SW1A 1AA")
    except Exception as exc:  # pragma: no cover - only used for the opt-in Stripe-hosted run.
        pytest.skip(f"Stripe-hosted card fields could not be filled reliably: {exc}")

    submit_candidates = [
        browser_page.get_by_role("button", name=re.compile(r"pay|subscribe", re.I)).first,
        browser_page.locator('button[type="submit"]').first,
    ]
    for locator in submit_candidates:
        try:
            locator.wait_for(timeout=2_000)
            locator.click()
            break
        except Exception:  # pragma: no cover - only used for the opt-in Stripe-hosted run.
            continue
    else:  # pragma: no cover - only used for the opt-in Stripe-hosted run.
        pytest.skip("Stripe Checkout submit button could not be located in the hosted page.")

    browser_page.wait_for_function("window.location.pathname.includes('/shop/success/')")
    assert browser_page.locator("h1").inner_text().strip().lower() == "order confirmed"
