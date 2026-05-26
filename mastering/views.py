"""Views for the mastering services site."""

from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.urls import reverse
from josephlovesjohn_site.assets import public_asset_url
from josephlovesjohn_site.rate_limits import is_rate_limited
from josephlovesjohn_site.recaptcha import verify_recaptcha_request
from josephlovesjohn_site.site_urls import absolute_site_url
from main_site.forms import ContactForm


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
