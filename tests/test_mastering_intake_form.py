"""Tests for the mastering intake form flow."""

from unittest.mock import patch

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture(autouse=True)
def clear_mastering_intake_rate_limits() -> None:
    cache.clear()
    yield
    cache.clear()


def _valid_intake_payload() -> dict:
    return {
        "submitter_role": "artist",
        "contact_email": "artist@example.com",
        "artist_name": "Example Artist",
        "track_title": "Example Track",
        "album_or_ep": "Example EP",
        "isrc_code": "GB-ABC-26-00001",
        "mix_file_details": "Final stereo WAV exported from the mix session.",
        "mix_file_link": "https://example.com/mix.wav",
        "sample_rate": "44.1kHz",
        "bit_depth": "24-bit",
        "peak_loudness_level": "-3 dBTP",
        "master_bus_processing": "Gentle bus compression only.",
        "limiting_clipping": "No limiter on the mix.",
        "desired_feel": "Open, warm, and loud enough for streaming.",
        "mix_concerns": "Keep the low end controlled.",
        "reference_tracks": "https://open.spotify.com/track/example",
        "reference_track_notes": "I like the width and warmth.",
        "release_formats": ["Streaming", "CD"],
        "deliverables": ["WAV", "MP3 reference"],
        "upload_confirmation": "https://example.com/artist-upload",
        "artist_loudness_processing": "No limiter, just a rough bounce.",
        "genre_vibe": "Warm alternative folk.",
        "artist_final_feel": "Wide, warm, and emotionally direct.",
        "artist_reference_tracks": "https://open.spotify.com/track/artist-reference",
        "artist_reference_notes": "The vocal warmth and soft low end.",
        "artist_release_formats": ["Streaming", "Bandcamp"],
        "artist_extra_notes": "I am unsure about the low end.",
        "multiple_tracks_notes": "Make the EP feel cohesive.",
        "deadline": "2026-06-15",
        "hard_deadline": "No",
        "extra_notes": "Thanks!",
    }


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
    RECAPTCHA_SITE_KEY="",
    RECAPTCHA_SECRET_KEY="",
)
def test_mastering_intake_form_sends_email_and_logs_sheet_payload(client) -> None:
    with patch("mastering.views._send_intake_to_google_sheets") as send_to_sheet:
        response = client.post(reverse("mastering:intake"), _valid_intake_payload())

    assert response.status_code == 302
    assert response["Location"] == reverse("mastering:intake")
    assert len(mail.outbox) == 1
    send_to_sheet.assert_called_once()

    sent_email = mail.outbox[0]
    assert sent_email.subject == "Mastering intake from Example Artist - Example Track"
    assert sent_email.to == ["josephlovesjohn@gmail.com"]
    assert sent_email.reply_to == ["artist@example.com"]
    assert "Mix file link: https://example.com/mix.wav" in sent_email.body
    assert "Intended release format(s): Streaming, CD" in sent_email.body
    assert "Which best describes you?: Artist" in sent_email.body
    assert "Sample rate: 44.1kHz" in sent_email.body
    assert "Bit depth: 24-bit" in sent_email.body

    sheet_payload = send_to_sheet.call_args.args[0]
    assert sheet_payload["headers"][0] == "Timestamp"
    assert sheet_payload["values"]["Artist name"] == "Example Artist"
    assert sheet_payload["values"]["Mix file details"] == "https://example.com/artist-upload"
    assert sheet_payload["values"]["Artist final master feel"] == "Wide, warm, and emotionally direct."
    assert sheet_payload["values"]["Artist release format(s)"] == "Streaming, Bandcamp"
    assert sheet_payload["values"]["Deliverables"] == "WAV, MP3 reference"
    assert sheet_payload["values"]["Master bus processing"] == "Gentle bus compression only."
    assert len(sheet_payload["row"]) == len(sheet_payload["headers"])


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
    RECAPTCHA_SITE_KEY="",
    RECAPTCHA_SECRET_KEY="",
)
def test_mastering_intake_form_accepts_engineer_branch(client) -> None:
    payload = _valid_intake_payload()
    payload.update(
        {
            "submitter_role": "engineer",
            "contact_email": "engineer@example.com",
            "engineer_name": "Mix Engineer",
            "client_contact_email": "artist@example.com",
        }
    )

    with patch("mastering.views._send_intake_to_google_sheets") as send_to_sheet:
        response = client.post(reverse("mastering:intake"), payload)

    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert "Which best describes you?: Mix engineer" in mail.outbox[0].body
    assert "Mix engineer name: Mix Engineer" in mail.outbox[0].body
    assert send_to_sheet.call_args.args[0]["values"]["Artist / client email"] == "artist@example.com"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="josephlovesjohn@gmail.com",
    CONTACT_RECIPIENT_EMAIL="josephlovesjohn@gmail.com",
    RECAPTCHA_SITE_KEY="",
    RECAPTCHA_SECRET_KEY="",
)
def test_mastering_intake_form_shows_validation_errors(client) -> None:
    response = client.post(
        reverse("mastering:intake"),
        {
            "contact_email": "not-an-email",
            "submitter_role": "artist",
            "artist_name": "",
            "track_title": "",
            "upload_confirmation": "not-a-url",
            "sample_rate": "",
            "bit_depth": "",
            "desired_feel": "",
        },
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "Please correct the highlighted fields and try again." in body
    assert "Enter a valid email address." in body
    assert "Enter a valid URL." in body
    assert len(mail.outbox) == 0
