"""Tests for the main-site contact form flow."""

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture(autouse=True)
def clear_contact_rate_limits() -> None:
    """Reset cache-backed rate limit state between contact-form tests."""
    cache.clear()
    yield
    cache.clear()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
    RECAPTCHA_SITE_KEY="",
    RECAPTCHA_SECRET_KEY="",
)
def test_contact_form_sends_email_and_redirects(client) -> None:
    """A valid contact submission should email the configured inbox."""
    response = client.post(
        reverse("main_site:contact"),
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "Hello from the website.",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert "Thanks, your message has been sent." in response.content.decode()
    assert len(mail.outbox) == 1

    sent_email = mail.outbox[0]
    assert sent_email.subject == "Website contact from Jane Doe"
    assert sent_email.to == ["josephlovesjohn@gmail.com"]
    assert sent_email.reply_to == ["jane@example.com"]
    assert "Hello from the website." in sent_email.body


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
)
def test_contact_form_shows_validation_errors(client) -> None:
    """Invalid contact submissions should stay on the page with errors."""
    response = client.post(
        reverse("main_site:contact"),
        {
            "name": "",
            "email": "not-an-email",
            "message": "",
        },
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "Please correct the highlighted fields and try again." in body
    assert "This field is required." in body
    assert "Enter a valid email address." in body
    assert len(mail.outbox) == 0


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
)
def test_contact_form_honeypot_discards_spam_without_sending_email(client) -> None:
    """Filled honeypot fields should pretend success without emailing the inbox."""
    response = client.post(
        reverse("main_site:contact"),
        {
            "name": "Bot Doe",
            "email": "bot@example.com",
            "message": "Spam message.",
            "website": "https://spam.example",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert "Thanks, your message has been sent." in response.content.decode()
    assert len(mail.outbox) == 0


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RATE_LIMIT_ATTEMPTS=1,
    CONTACT_RATE_LIMIT_WINDOW=3600,
    RECAPTCHA_SITE_KEY="",
    RECAPTCHA_SECRET_KEY="",
)
def test_contact_form_rate_limit_blocks_repeated_messages(client) -> None:
    """Repeated valid contact submissions should be rate limited."""
    first_response = client.post(
        reverse("main_site:contact"),
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "First message.",
        },
        follow=True,
    )
    second_response = client.post(
        reverse("main_site:contact"),
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "Second message.",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert "Too many messages have been sent" in second_response.content.decode()
    assert len(mail.outbox) == 1


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
    RECAPTCHA_SITE_KEY="site-key",
    RECAPTCHA_SECRET_KEY="secret-key",
)
def test_contact_form_blocks_failed_recaptcha(client, monkeypatch) -> None:
    """Protected contact submissions should stop when reCAPTCHA verification fails."""
    monkeypatch.setattr("main_site.views.verify_recaptcha_request", lambda request, expected_action: False)

    response = client.post(
        reverse("main_site:contact"),
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "Hello from the website.",
            "g-recaptcha-response": "bad-token",
        },
    )

    assert response.status_code == 200
    assert "We could not verify this message." in response.content.decode()
    assert len(mail.outbox) == 0


@override_settings(RECAPTCHA_SITE_KEY="site-key", RECAPTCHA_SECRET_KEY="secret-key")
def test_contact_page_renders_recaptcha_v3_hook(client) -> None:
    """The contact form should include the invisible reCAPTCHA v3 client hook when enabled."""
    response = client.get(reverse("main_site:contact"))
    body = response.content.decode()

    assert 'data-recaptcha-action="contact"' in body
    assert 'name="g-recaptcha-response"' in body
    assert "https://www.google.com/recaptcha/api.js?render=site-key" in body


def test_contact_page_does_not_render_shop_cart_messages(client) -> None:
    """Shop checkout notices should not leak into the contact article."""
    checkout_response = client.get(reverse("shop:checkout"))

    assert checkout_response.status_code == 302

    response = client.get(reverse("main_site:contact"))
    body = response.content.decode()

    assert response.status_code == 200
    assert "Your cart is empty. Add a track from the music page to continue." not in body
    assert "contact-form-messages" not in body


def test_contact_page_renders_only_instagram_and_tiktok_icons(client) -> None:
    """The contact page should expose only the supported social messaging links."""
    response = client.get(reverse("main_site:contact"))
    body = response.content.decode()

    assert response.status_code == 200
    assert 'href="https://ig.me/m/josephlovesjohn_music"' in body
    assert 'href="https://www.tiktok.com/@joseph_loves_john"' in body
    assert "fa-instagram" in body
    assert "fa-tiktok" in body
    assert "fa-twitter" not in body
    assert "fa-facebook-f" not in body
    assert "fa-github" not in body
