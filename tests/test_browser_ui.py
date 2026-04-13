"""Browser-level tests for the main site and mastering UI flows."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.browser, pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def _route_url(live_server, route_name: str, *args, **kwargs) -> str:
    """Build an absolute route URL for Playwright browser tests."""
    return f"{live_server.url}{reverse(route_name, args=args, kwargs=kwargs)}"



def test_intro_route_sets_hash_and_activates_intro_article(browser_page, live_server) -> None:
    """The intro route should land the user directly in the intro article."""
    browser_page.goto(_route_url(live_server, "main_site:intro"), wait_until="load")
    browser_page.wait_for_selector("article#intro.active")

    assert browser_page.evaluate("window.location.hash") == "#intro"
    assert browser_page.locator("article#intro.active").is_visible()
    assert browser_page.locator(".intro-signup-form").is_visible()
    assert browser_page.locator('script[data-uid="408ee57c19"]').count() == 1



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



def test_mastering_transition_and_menu_open_works_from_main_site(browser_page, live_server) -> None:
    """The mastering CTA should preserve transition state and expose the menu UI."""
    browser_page.goto(_route_url(live_server, "main_site:main"), wait_until="load")
    browser_page.locator('#top-nav a[data-mastering-link="true"]').click()
    browser_page.wait_for_url("**/mastering-services/?from_home=1")

    body_class = browser_page.locator("body").get_attribute("class") or ""
    assert "is-from-home" in body_class

    browser_page.locator("a.mastering-menu-trigger").click()
    browser_page.wait_for_function("document.body.classList.contains('is-menu-visible')")
    assert browser_page.locator("#menu .close").is_visible()
    assert browser_page.locator('#menu a[href="#services"]').is_visible()
