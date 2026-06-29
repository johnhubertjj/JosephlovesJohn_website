"""Shared public contact form submission workflow."""

from dataclasses import dataclass

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from josephlovesjohn_site.rate_limits import is_rate_limited
from josephlovesjohn_site.recaptcha import verify_recaptcha_request


@dataclass(frozen=True)
class ContactSubmissionResult:
    """Outcome of processing a contact form POST."""

    should_redirect: bool = False


def handle_contact_submission(request, form) -> ContactSubmissionResult:
    """Validate, protect, and send a public contact form submission."""
    if not form.is_valid():
        messages.error(
            request,
            "Please correct the highlighted fields and try again.",
            extra_tags="contact",
        )
        return ContactSubmissionResult()

    cleaned = form.cleaned_data
    if cleaned.get("website"):
        messages.success(request, "Thanks, your message has been sent.", extra_tags="contact")
        return ContactSubmissionResult(should_redirect=True)

    if not verify_recaptcha_request(request, expected_action="contact"):
        messages.error(
            request,
            "We could not verify this message. Please refresh the page and try again.",
            extra_tags="contact",
        )
        return ContactSubmissionResult()

    if is_rate_limited(
        request,
        scope="contact-form",
        limit=settings.CONTACT_RATE_LIMIT_ATTEMPTS,
        window_seconds=settings.CONTACT_RATE_LIMIT_WINDOW,
        extra_identifier=cleaned["email"],
    ):
        messages.error(
            request,
            "Too many messages have been sent from this connection. Please try again later.",
            extra_tags="contact",
        )
        return ContactSubmissionResult()

    message_body = (
        f"New website contact form submission\n\n"
        f"Name: {cleaned['name']}\n"
        f"Email: {cleaned['email']}\n\n"
        f"Message:\n{cleaned['message']}"
    )
    email_message = EmailMessage(
        subject=f"Website contact from {cleaned['name']}",
        body=message_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_RECIPIENT_EMAIL],
        reply_to=[cleaned["email"]],
    )
    try:
        email_message.send(fail_silently=False)
    except Exception:  # pragma: no cover - exercised in production mail failures.
        messages.error(
            request,
            "Your message could not be sent right now. Please try again in a moment.",
            extra_tags="contact",
        )
        return ContactSubmissionResult()

    messages.success(request, "Thanks, your message has been sent.", extra_tags="contact")
    return ContactSubmissionResult(should_redirect=True)
