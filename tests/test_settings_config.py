"""Tests for environment-driven Django settings helpers."""

import pytest

from josephlovesjohn_site import settings

pytestmark = pytest.mark.smoke


def test_env_bool_parses_truthy_and_falsy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boolean helper should understand common truthy and falsy env values."""
    monkeypatch.setenv("TEST_BOOL", "yes")
    assert settings._env_bool("TEST_BOOL") is True

    monkeypatch.setenv("TEST_BOOL", "0")
    assert settings._env_bool("TEST_BOOL", default=True) is False


def test_env_int_falls_back_for_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integer helper should fall back safely for invalid env values."""
    monkeypatch.setenv("TEST_INT", "42")
    assert settings._env_int("TEST_INT", default=1) == 42

    monkeypatch.setenv("TEST_INT", "invalid")
    assert settings._env_int("TEST_INT", default=7) == 7


def test_env_list_strips_blank_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    """List helper should return normalized comma-separated values."""
    monkeypatch.setenv("TEST_LIST", "example.com, www.example.com, ,api.example.com")

    assert settings._env_list("TEST_LIST") == [
        "example.com",
        "www.example.com",
        "api.example.com",
    ]
