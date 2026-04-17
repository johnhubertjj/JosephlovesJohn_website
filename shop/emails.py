"""Email helpers for paid order confirmations and download access."""

from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.signing import BadSignature, SignatureExpired, dumps, loads
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .models import Order, OrderItem

DOWNLOAD_ACCESS_TOKEN_SALT = "shop.download-email-access"
DOWNLOAD_ACCESS_MAX_AGE = 60 * 60 * 24 * 30


def build_download_access_token(item: OrderItem) -> str:
    """Return a signed token that grants email-based access to one order item."""
    return dumps(
        {
            "item_id": item.pk,
            "order_id": item.order_id,
        },
        salt=DOWNLOAD_ACCESS_TOKEN_SALT,
    )


def has_valid_download_access_token(item: OrderItem, token: str) -> bool:
    """Return whether a supplied email-download token matches the order item."""
    if not token:
        return False

    try:
        payload = loads(
            token,
            salt=DOWNLOAD_ACCESS_TOKEN_SALT,
            max_age=DOWNLOAD_ACCESS_MAX_AGE,
        )
    except (BadSignature, SignatureExpired):
        return False

    return payload == {"item_id": item.pk, "order_id": item.order_id}


def _download_link(request, item: OrderItem) -> str:
    """Build the absolute emailed download URL for a purchased item."""
    query = urlencode({"access": build_download_access_token(item)})
    path = reverse("shop:download", kwargs={"item_id": item.pk})
    return request.build_absolute_uri(f"{path}?{query}")


def _download_links(request, item: OrderItem) -> list[tuple[str, str]]:
    """Return all absolute emailed download URLs for a purchased item."""
    links = [("MP3", _download_link(request, item))]
    if item.download_file_wav_path:
        query = urlencode({"access": build_download_access_token(item), "format": "wav"})
        path = reverse("shop:download", kwargs={"item_id": item.pk})
        links.append(("WAV", request.build_absolute_uri(f"{path}?{query}")))
    return links


def send_order_confirmation_email(request, order: Order) -> bool:
    """Send the post-payment download email once for a confirmed order."""
    if not order.email:
        return False

    with transaction.atomic():
        locked_order = Order.objects.select_for_update().prefetch_related("items").get(pk=order.pk)
        if not locked_order.is_paid or locked_order.confirmation_email_sent_at is not None or not locked_order.email:
            order.confirmation_email_sent_at = locked_order.confirmation_email_sent_at
            return False

        lines = [
            f"Hello {locked_order.full_name or 'there'},",
            "",
            "Thanks for your order from JosephlovesJohn.",
            f"Order #{locked_order.pk} has been confirmed and your download links are ready below.",
            "",
        ]
        for item in locked_order.items.all():
            lines.append(f"- {item.title_snapshot}")
            for label, link in _download_links(request, item):
                lines.append(f"  {label}: {link}")

        lines.extend(
            [
                "",
                "These links stay active for 30 days from the email date.",
                f"If you need any help, email {settings.BUSINESS_CONTACT_EMAIL}.",
            ]
        )

        email_message = EmailMessage(
            subject=f"Your JosephlovesJohn downloads for order #{locked_order.pk}",
            body="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[locked_order.email],
            reply_to=[settings.BUSINESS_CONTACT_EMAIL] if settings.BUSINESS_CONTACT_EMAIL else None,
        )
        email_message.send(fail_silently=False)

        locked_order.confirmation_email_sent_at = timezone.now()
        locked_order.save(update_fields=["confirmation_email_sent_at"])
        order.confirmation_email_sent_at = locked_order.confirmation_email_sent_at
        return True
