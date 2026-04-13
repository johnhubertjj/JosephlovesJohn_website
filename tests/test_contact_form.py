"""Tests for the main-site contact form flow."""

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
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
