"""Black-box tests for the Django management entrypoint."""

import os
import sys

import django.core.management
import manage
import pytest

pytestmark = pytest.mark.smoke


def test_main_sets_default_settings_and_executes_command(monkeypatch):
    """The management entrypoint should set settings and delegate to Django."""
    called: dict[str, list[str]] = {}

    def fake_execute(argv: list[str]) -> None:
        called["argv"] = list(argv)

    monkeypatch.delenv("DJANGO_SETTINGS_MODULE", raising=False)
    monkeypatch.setattr(sys, "argv", ["manage.py", "check"])
    monkeypatch.setattr(django.core.management, "execute_from_command_line", fake_execute)

    manage.main()

    assert os.environ["DJANGO_SETTINGS_MODULE"] == "josephlovesjohn_site.settings"
    assert called["argv"] == ["manage.py", "check"]
