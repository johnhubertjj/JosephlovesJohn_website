"""Views for the mastering services site."""

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from josephlovesjohn_site.assets import public_asset_url
from josephlovesjohn_site.rate_limits import is_rate_limited
from josephlovesjohn_site.recaptcha import verify_recaptcha_request
from josephlovesjohn_site.site_urls import absolute_site_url
from main_site.forms import ContactForm

from .forms import MasteringIntakeForm

logger = logging.getLogger(__name__)


INTAKE_SHEET_COLUMNS = [
    ("submitted_at", "Timestamp"),
    ("submitter_role", "Which best describes you?"),
    ("contact_email", "Contact email"),
    ("engineer_name", "Mix engineer name"),
    ("client_contact_email", "Artist / client email"),
    ("artist_name", "Artist name"),
    ("track_title", "Track title"),
    ("album_or_ep", "Album/EP name"),
    ("isrc_code", "ISRC code"),
    ("mix_file_details", "Mix file details"),
    ("mix_file_link", "Mix file link"),
    ("sample_rate", "Sample rate"),
    ("bit_depth", "Bit depth"),
    ("peak_loudness_level", "Peak loudness level"),
    ("master_bus_processing", "Master bus processing"),
    ("limiting_clipping", "Limiting / clipping / loudness maximisation"),
    ("desired_feel", "Desired master feel"),
    ("mix_concerns", "Specific mix concerns"),
    ("reference_tracks", "Reference track(s)"),
    ("reference_track_notes", "Reference track notes"),
    ("release_formats", "Intended release format(s)"),
    ("deliverables", "Deliverables"),
    ("artist_loudness_processing", "Artist loudness and processing (if known)"),
    ("genre_vibe", "Genre/vibe"),
    ("artist_final_feel", "Artist final master feel"),
    ("artist_reference_tracks", "Artist reference track(s)"),
    ("artist_reference_notes", "Artist reference track notes"),
    ("artist_release_formats", "Artist release format(s)"),
    ("artist_extra_notes", "Artist extra notes"),
    ("multiple_tracks_notes", "Multiple track notes"),
    ("deadline", "Desired delivery date"),
    ("hard_deadline", "Hard deadline?"),
    ("extra_notes", "Extra notes"),
]


def _format_intake_value(value):
    if isinstance(value, list):
        return ", ".join(value) if value else "-"
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    if value:
        return str(value)
    return "-"


def _intake_payload(cleaned):
    formatted = {
        field: _format_intake_value(cleaned.get(field))
        for field, _column in INTAKE_SHEET_COLUMNS
        if field != "submitted_at"
    }
    if formatted.get("submitter_role") == "artist":
        formatted["submitter_role"] = "Artist"
    elif formatted.get("submitter_role") == "engineer":
        formatted["submitter_role"] = "Mix engineer"
    if formatted.get("submitter_role") == "Artist":
        formatted["mix_file_details"] = _format_intake_value(cleaned.get("upload_confirmation"))
    formatted["submitted_at"] = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S %Z")
    values = {}
    for field, column in INTAKE_SHEET_COLUMNS:
        values[column] = formatted[field]
    return {
        "headers": [column for _field, column in INTAKE_SHEET_COLUMNS],
        "row": [values[column] for _field, column in INTAKE_SHEET_COLUMNS],
        "values": values,
    }


def _send_intake_to_google_sheets(payload):
    webhook_url = settings.MASTERING_INTAKE_GOOGLE_SHEETS_WEBHOOK_URL
    if not webhook_url:
        return False

    data = json.dumps(payload).encode("utf-8")
    request = Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            if 200 <= response.status < 300:
                return True
            logger.warning("Mastering intake Google Sheets webhook returned HTTP %s", response.status)
            return False
    except (OSError, URLError, TimeoutError) as exc:
        logger.warning("Mastering intake Google Sheets webhook failed: %s", exc)
        return False


def _intake_email_body(payload):
    lines = ["New mastering intake form submission", ""]
    values = payload["values"]
    for _field, column in INTAKE_SHEET_COLUMNS:
        lines.append(f"{column}: {values[column]}")
    return "\n".join(lines)


def _intake_context(request, *, form=None):
    return {
        "form": form or MasteringIntakeForm(),
        "seo": {
            "title": "Mastering Intake Form | John Joseph Mastering",
            "description": "Private intake form for John Joseph Mastering projects.",
            "canonical_url": absolute_site_url(request.path),
            "image_url": absolute_site_url(public_asset_url("mastering/images/mastering-website-header-image.jpg")),
            "robots": "noindex,follow",
        },
    }


def _home_context(request, *, contact_form=None):
    contact_messages = [
        message
        for message in get_messages(request)
        if "contact" in message.extra_tags.split()
    ]
    return {
        "entered_from_home": request.GET.get("from_home") == "1",
        "contact_form": contact_form or ContactForm(),
        "contact_messages": contact_messages,
        "seo": {
            "title": "John Joseph Mastering | JosephlovesJohn",
            "description": (
                "Independent, taste-first mastering services from JosephlovesJohn, focused on depth, clarity, "
                "and emotional translation."
            ),
            "canonical_url": absolute_site_url(request.path),
            "image_url": absolute_site_url(public_asset_url("mastering/images/mastering-website-header-image.jpg")),
            "robots": "index,follow",
        },
    }


def home(request):
    """Render the mastering services landing page.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :returns: A rendered response for the mastering home page.
    :rtype: django.http.HttpResponse
    """
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            if cleaned.get("website"):
                messages.success(request, "Thanks, your message has been sent.", extra_tags="contact")
                return redirect(f"{reverse('mastering:home')}#contact")
            if not verify_recaptcha_request(request, expected_action="contact"):
                messages.error(
                    request,
                    "We could not verify this message. Please refresh the page and try again.",
                    extra_tags="contact",
                )
                return render(request, "mastering/home.html", _home_context(request, contact_form=form))
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
                return render(request, "mastering/home.html", _home_context(request, contact_form=form))
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
                return render(request, "mastering/home.html", _home_context(request, contact_form=form))

            messages.success(request, "Thanks, your message has been sent.", extra_tags="contact")
            return redirect(f"{reverse('mastering:home')}#contact")

        messages.error(
            request,
            "Please correct the highlighted fields and try again.",
            extra_tags="contact",
        )
        return render(request, "mastering/home.html", _home_context(request, contact_form=form))

    return render(request, "mastering/home.html", _home_context(request))


def intake(request):
    """Render and process the mastering project intake form."""

    if request.method == "POST":
        form = MasteringIntakeForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            if cleaned.get("website"):
                messages.success(request, "Thanks, your intake form has been sent.")
                return redirect(reverse("mastering:intake"))
            if not verify_recaptcha_request(request, expected_action="mastering_intake"):
                messages.error(request, "We could not verify this form. Please refresh the page and try again.")
                return render(request, "mastering/intake.html", _intake_context(request, form=form))
            if is_rate_limited(
                request,
                scope="mastering-intake-form",
                limit=settings.CONTACT_RATE_LIMIT_ATTEMPTS,
                window_seconds=settings.CONTACT_RATE_LIMIT_WINDOW,
                extra_identifier=cleaned["contact_email"],
            ):
                messages.error(
                    request,
                    "Too many forms have been sent from this connection. Please try again later.",
                )
                return render(request, "mastering/intake.html", _intake_context(request, form=form))

            payload = _intake_payload(cleaned)
            email_message = EmailMessage(
                subject=f"Mastering intake from {cleaned['artist_name']} - {cleaned['track_title']}",
                body=_intake_email_body(payload),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.CONTACT_RECIPIENT_EMAIL],
                reply_to=[cleaned["contact_email"]],
            )
            try:
                email_message.send(fail_silently=False)
            except Exception:  # pragma: no cover - exercised in production mail failures.
                messages.error(request, "Your intake form could not be sent right now. Please try again in a moment.")
                return render(request, "mastering/intake.html", _intake_context(request, form=form))

            sheet_logged = _send_intake_to_google_sheets(payload)
            if sheet_logged or not settings.MASTERING_INTAKE_GOOGLE_SHEETS_WEBHOOK_URL:
                messages.success(request, "Thanks, your intake form has been sent.")
            else:
                messages.success(
                    request,
                    "Thanks, your intake form has been sent. Sheet logging could not be confirmed.",
                )
            return redirect(reverse("mastering:intake"))

        messages.error(request, "Please correct the highlighted fields and try again.")
        return render(request, "mastering/intake.html", _intake_context(request, form=form))

    return render(request, "mastering/intake.html", _intake_context(request))


def subfolder(request, subfolder):
    """Render a placeholder page for a mastering subfolder.

    :param request: The incoming HTTP request.
    :type request: django.http.HttpRequest
    :param subfolder: The requested mastering subsection slug.
    :type subfolder: str
    :returns: A rendered response for the requested placeholder page.
    :rtype: django.http.HttpResponse
    """
    return render(
        request,
        "mastering/subfolder.html",
        {
            "subfolder": subfolder,
            "seo": {
                "title": f"{subfolder.replace('-', ' ').title()} | John Joseph Mastering | JosephlovesJohn",
                "description": "Reserved placeholder page for a future JosephlovesJohn mastering services subsection.",
                "canonical_url": absolute_site_url(request.path),
                "image_url": absolute_site_url(public_asset_url("images/jlovesj_symbol-my_version3.png")),
                "robots": "noindex,follow",
            },
        },
    )
