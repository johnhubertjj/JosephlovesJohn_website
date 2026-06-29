"""Tests for the mastering-site contact form flow."""

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture(autouse=True)
def clear_mastering_contact_rate_limits() -> None:
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
def test_mastering_contact_form_sends_email_and_redirects_to_contact(client) -> None:
    response = client.post(
        reverse("mastering:home"),
        {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "message": "Hello about mastering.",
        },
    )

    assert response.status_code == 302
    assert response["Location"] == f"{reverse('mastering:home')}#contact"
    assert len(mail.outbox) == 1

    sent_email = mail.outbox[0]
    assert sent_email.subject == "Website contact from Jane Doe"
    assert sent_email.to == ["josephlovesjohn@gmail.com"]
    assert sent_email.reply_to == ["jane@example.com"]
    assert "Hello about mastering." in sent_email.body


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
)
def test_mastering_contact_form_shows_validation_errors(client) -> None:
    response = client.post(
        reverse("mastering:home"),
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
