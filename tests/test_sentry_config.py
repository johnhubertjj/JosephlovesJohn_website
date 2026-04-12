"""Tests for optional Sentry bootstrap behavior."""

import pytest
from josephlovesjohn_site import sentry

pytestmark = pytest.mark.smoke


def test_setup_sentry_from_env_skips_when_dsn_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sentry should stay disabled when no DSN is configured."""

    def fail_loader() -> tuple[object, object]:
        raise AssertionError("Sentry SDK should not be imported without a DSN.")

    monkeypatch.setattr(sentry, "_load_sentry_sdk", fail_loader)

    assert sentry.setup_sentry_from_env({}) is False


def test_setup_sentry_from_env_initializes_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sentry should initialize with the parsed environment configuration."""
    called: dict[str, object] = {}

    def fake_init(**kwargs: object) -> None:
        called.update(kwargs)

    class FakeDjangoIntegration:
        pass

    monkeypatch.setattr(sentry, "_load_sentry_sdk", lambda: (fake_init, FakeDjangoIntegration))

    configured = sentry.setup_sentry_from_env(
        {
            "SENTRY_DSN": "https://examplePublicKey@o0.ingest.sentry.io/0",
            "SENTRY_ENVIRONMENT": "production",
            "SENTRY_RELEASE": "2026.04.12",
            "SENTRY_TRACES_SAMPLE_RATE": "0.25",
            "SENTRY_SEND_DEFAULT_PII": "true",
            "SENTRY_DEBUG": "1",
        }
    )

    assert configured is True
    assert called["debug"] is True
    assert called["dsn"] == "https://examplePublicKey@o0.ingest.sentry.io/0"
    assert called["environment"] == "production"
    assert called["release"] == "2026.04.12"
    assert called["send_default_pii"] is True
    assert called["traces_sample_rate"] == 0.25
    assert len(called["integrations"]) == 1
    assert isinstance(called["integrations"][0], FakeDjangoIntegration)


def test_setup_sentry_from_env_falls_back_for_invalid_sample_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid numeric input should fall back to the safe default."""
    called: dict[str, object] = {}

    def fake_init(**kwargs: object) -> None:
        called.update(kwargs)

    class FakeDjangoIntegration:
        pass

    monkeypatch.setattr(sentry, "_load_sentry_sdk", lambda: (fake_init, FakeDjangoIntegration))

    sentry.setup_sentry_from_env(
        {
            "SENTRY_DSN": "https://examplePublicKey@o0.ingest.sentry.io/0",
            "SENTRY_TRACES_SAMPLE_RATE": "not-a-number",
        }
    )

    assert called["traces_sample_rate"] == 0.0
